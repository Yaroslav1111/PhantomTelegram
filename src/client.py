import json
import socket
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Optional

from pynput import keyboard


class KeyMirrorClient:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Key Mirror Client")
        self.controller = keyboard.Controller()

        self.connection: Optional[socket.socket] = None
        self.listener_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        self.server_host = tk.StringVar(value="127.0.0.1")
        self.server_port = tk.IntVar(value=8765)
        self.copy_enabled = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Отключено")
        self.latency_var = tk.StringVar(value="—")

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.grid(column=0, row=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        ttk.Label(frame, text="Сервер").grid(column=0, row=0, sticky="w")
        ttk.Entry(frame, textvariable=self.server_host, width=18).grid(
            column=1, row=0, sticky="we", padx=4
        )
        ttk.Entry(frame, textvariable=self.server_port, width=7).grid(
            column=2, row=0, sticky="we"
        )
        self.connect_btn = ttk.Button(frame, text="Подключиться", command=self.connect)
        self.connect_btn.grid(column=3, row=0, padx=4)
        self.disconnect_btn = ttk.Button(
            frame, text="Отключиться", command=self.disconnect, state="disabled"
        )
        self.disconnect_btn.grid(column=4, row=0)

        ttk.Label(frame, text="Статус:").grid(column=0, row=1, sticky="w", pady=(8, 0))
        ttk.Label(frame, textvariable=self.status_var).grid(column=1, row=1, sticky="w")
        ttk.Label(frame, text="Задержка:").grid(column=2, row=1, sticky="e", pady=(8, 0))
        ttk.Label(frame, textvariable=self.latency_var).grid(column=3, row=1, sticky="w")

        self.copy_check = ttk.Checkbutton(
            frame, text="Копировать ввод", variable=self.copy_enabled
        )
        self.copy_check.grid(column=0, row=2, columnspan=2, sticky="w", pady=(8, 0))

        ttk.Label(frame, text="Последние нажатия:").grid(
            column=0, row=3, columnspan=5, sticky="w", pady=(10, 2)
        )
        self.log = tk.Text(frame, height=10, width=60, state="disabled")
        self.log.grid(column=0, row=4, columnspan=5, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=0)
        frame.columnconfigure(3, weight=0)
        frame.columnconfigure(4, weight=0)
        frame.rowconfigure(4, weight=1)

    def connect(self):
        if self.listener_thread and self.listener_thread.is_alive():
            return

        host = self.server_host.get().strip()
        port = int(self.server_port.get())

        try:
            conn = socket.create_connection((host, port), timeout=5)
        except OSError as exc:
            self.status_var.set(f"Ошибка подключения: {exc}")
            return

        self.connection = conn
        self.stop_event.clear()
        self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listener_thread.start()

        self.status_var.set("Подключено")
        self.connect_btn.configure(state="disabled")
        self.disconnect_btn.configure(state="normal")

    def disconnect(self):
        self.stop_event.set()
        conn = self.connection
        self.connection = None
        if conn:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                conn.close()
            except OSError:
                pass
        if self.listener_thread:
            self.listener_thread.join(timeout=2)
        self.listener_thread = None
        self.status_var.set("Отключено")
        self.latency_var.set("—")
        self.connect_btn.configure(state="normal")
        self.disconnect_btn.configure(state="disabled")

    def _append_log(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _apply_key(self, key: str):
        if not key:
            return
        if len(key) == 1:
            self.controller.press(key)
            self.controller.release(key)
            return

        mapping = {
            "{return}": keyboard.Key.enter,
            "{backspace}": keyboard.Key.backspace,
            "{tab}": keyboard.Key.tab,
            "{escape}": keyboard.Key.esc,
            "{caps_lock}": keyboard.Key.caps_lock,
            " ": keyboard.Key.space,
        }
        mapped = mapping.get(key)
        if mapped:
            self.controller.press(mapped)
            self.controller.release(mapped)

    def _handle_message(self, payload: dict):
        if payload.get("type") != "key":
            return
        key = payload.get("key", "")
        ts = payload.get("ts")
        latency_ms = "—"
        if ts is not None:
            latency_ms = f"{(time.time() - ts) * 1000:.1f} мс"
            self.latency_var.set(latency_ms)

        display = key.replace("\n", "\\n")
        self._append_log(display)

        if self.copy_enabled.get():
            self._apply_key(key)

    def _listen_loop(self):
        conn = self.connection
        if conn is None:
            return
        file_obj = conn.makefile("r")
        while not self.stop_event.is_set():
            try:
                line = file_obj.readline()
            except OSError:
                break
            if not line:
                break
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            self.root.after(0, self._handle_message, payload)
        self.root.after(0, self.disconnect)


if __name__ == "__main__":
    tk_root = tk.Tk()
    app = KeyMirrorClient(tk_root)
    tk_root.protocol("WM_DELETE_WINDOW", app.disconnect)
    tk_root.mainloop()
