import asyncio
import contextlib
import json
import os
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Optional

from dotenv import load_dotenv
from pynput import keyboard
from telethon import TelegramClient, events

load_dotenv()

API_ID = int(os.getenv("LOGGER_API_ID", "0"))
API_HASH = os.getenv("LOGGER_API_HASH", "")
SESSION_NAME = os.getenv("LOGGER_SESSION_NAME", "client_session")
SERVER_BOT_USERNAME = os.getenv("LOGGER_SERVER_BOT_USERNAME", "")


class TelegramKeyMirrorClient:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Key Mirror Client")
        self.controller = keyboard.Controller()

        self.server_bot_username = tk.StringVar(value=SERVER_BOT_USERNAME)
        self.copy_enabled = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Отключено")
        self.latency_var = tk.StringVar(value="—")

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._client: Optional[TelegramClient] = None
        self.listener_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.grid(column=0, row=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        ttk.Label(frame, text="Bot username").grid(column=0, row=0, sticky="w")
        ttk.Entry(frame, textvariable=self.server_bot_username, width=24).grid(
            column=1, row=0, sticky="we", padx=4
        )
        self.connect_btn = ttk.Button(frame, text="Подключиться", command=self.connect)
        self.connect_btn.grid(column=2, row=0, padx=4)
        self.disconnect_btn = ttk.Button(
            frame, text="Отключиться", command=self.disconnect, state="disabled"
        )
        self.disconnect_btn.grid(column=3, row=0)

        ttk.Label(frame, text="Статус:").grid(column=0, row=1, sticky="w", pady=(8, 0))
        ttk.Label(frame, textvariable=self.status_var).grid(column=1, row=1, sticky="w")
        ttk.Label(frame, text="Задержка:").grid(column=2, row=1, sticky="e", pady=(8, 0))
        ttk.Label(frame, textvariable=self.latency_var).grid(column=3, row=1, sticky="w")

        self.copy_check = ttk.Checkbutton(
            frame, text="Копировать ввод", variable=self.copy_enabled
        )
        self.copy_check.grid(column=0, row=2, columnspan=2, sticky="w", pady=(8, 0))

        ttk.Label(frame, text="Последние нажатия:").grid(
            column=0, row=3, columnspan=4, sticky="w", pady=(10, 2)
        )
        self.log = tk.Text(frame, height=10, width=60, state="disabled")
        self.log.grid(column=0, row=4, columnspan=4, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=0)
        frame.columnconfigure(3, weight=0)
        frame.rowconfigure(4, weight=1)

    def connect(self):
        if self.listener_thread and self.listener_thread.is_alive():
            return
        if API_ID == 0 or not API_HASH:
            self.status_var.set("Заполните LOGGER_API_ID и LOGGER_API_HASH в .env")
            return

        self.stop_event.clear()
        self.listener_thread = threading.Thread(target=self._run_client_loop, daemon=True)
        self.listener_thread.start()
        self.status_var.set("Подключаемся…")
        self.connect_btn.configure(state="disabled")
        self.disconnect_btn.configure(state="normal")

    def disconnect(self):
        self.stop_event.set()
        loop = self._loop
        client = self._client
        if loop and client:
            asyncio.run_coroutine_threadsafe(client.disconnect(), loop)
        if self.listener_thread:
            self.listener_thread.join(timeout=5)
        self.listener_thread = None
        self._client = None
        self._loop = None
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
            if key == "\b":
                mapped = keyboard.Key.backspace
            elif key == "\n":
                mapped = keyboard.Key.enter
            elif key == "\t":
                mapped = keyboard.Key.tab
            else:
                mapped = key

            if isinstance(mapped, keyboard.Key):
                self.controller.press(mapped)
                self.controller.release(mapped)
                return

            self.controller.press(key)
            self.controller.release(key)
            return

        if key == "{escape}":
            mapped = keyboard.Key.esc
        else:
            mapped = None
        if mapped:
            self.controller.press(mapped)
            self.controller.release(mapped)

    def _handle_payload(self, payload: dict):
        key = payload.get("key", "")
        ts = payload.get("ts")
        if ts is not None:
            self.latency_var.set(f"{(time.time() - ts) * 1000:.1f} мс")
        display = key.replace("\n", "\\n")
        self._append_log(display)
        if self.copy_enabled.get():
            self._apply_key(key)

    def _handle_plain_key(self, text: str, server_ts: Optional[float]):
        if server_ts is not None:
            self.latency_var.set(f"{(time.time() - server_ts) * 1000:.1f} мс")
        display = text.replace("\n", "\\n")
        self._append_log(display)
        if self.copy_enabled.get():
            self._apply_key(text)

    async def _handle_raw_message(self, event):
        sender = await event.get_sender()
        username = getattr(sender, "username", "") or ""
        if not getattr(sender, "bot", False):
            return
        target = self.server_bot_username.get().strip().lower()
        if not target or username.lower() != target:
            return

        text = event.raw_text or ""
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            server_ts = None
            if event.message and event.message.date:
                server_ts = event.message.date.timestamp()
            self.root.after(0, self._handle_plain_key, text, server_ts)
            return
        self.root.after(0, self._handle_payload, payload)

    async def _client_loop(self):
        self._client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        try:
            await self._client.start()
        except Exception as exc:
            self.root.after(0, self.status_var.set, f"Ошибка подключения: {exc}")
            return

        self._client.add_event_handler(self._handle_raw_message, events.NewMessage)
        self.root.after(0, self.status_var.set, "Подключено")
        run_task = asyncio.create_task(self._client.run_until_disconnected())

        try:
            while not self.stop_event.is_set():
                await asyncio.sleep(0.2)
        finally:
            await self._client.disconnect()
            run_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await run_task

    def _run_client_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            loop.run_until_complete(self._client_loop())
        finally:
            loop.close()
            self.root.after(0, self.disconnect)


if __name__ == "__main__":
    tk_root = tk.Tk()
    app = TelegramKeyMirrorClient(tk_root)
    tk_root.protocol("WM_DELETE_WINDOW", app.disconnect)
    tk_root.mainloop()
