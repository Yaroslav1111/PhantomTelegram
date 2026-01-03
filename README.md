# PhantomTelegram

**PhantomTelegram** is a lightweight Windows control bot written in Python (Telethon) that lets you управляйте питанием ПК через Telegram.

## Features
- Выключение/перезагрузка ПК.
- Сон, гибернация, блокировка.
- Отключение экрана и таймер выключения.

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
   The project depends on `telethon` for the Telegram bot.
5. **Set Your Config:**
   Set environment variables (PowerShell example):
   ```powershell
   $env:TELEGRAM_API_ID="123456"
   $env:TELEGRAM_API_HASH="your_api_hash"
   $env:TELEGRAM_BOT_TOKEN="123456:bot_token"
   $env:TELEGRAM_CHAT_ID="123456789"
   ```
6. **Run the Program:**
   ```bash
   python -m src.main
   ```

## Building a Hidden Windows Executable

To bundle the logger into a background Windows executable that runs without a console window:

1. Install [PyInstaller](https://pyinstaller.org/en/stable/):
   ```bash
   pip install pyinstaller
   ```
2. Build the executable:
   ```bash
   pyinstaller --onefile --noconsole --name PhantomTelegram src/main.py
   ```
3. The generated `dist/PhantomTelegram.exe` starts without appearing on the taskbar or showing a console window.

## License
**PhantomTelegram** is licensed under [The Unlicense](LICENSE), so feel free to use, modify, and distribute it as you like.

## Troubleshooting

- **`No matching distribution found` during `pip install`:** Ensure you are using a modern Python (3.10+) and upgrade `pip` inside your virtual environment with `python -m pip install --upgrade pip`. Old system-managed pips (e.g., 9.x) cannot see modern package releases.
- **`alembic: command not found`:** The project does not use Alembic or any database migrations—skip that step entirely.

---

**Disclaimer:** This project is intended for personal, authorized use only. The author assumes no responsibility for misuse.
