import asyncio
import ctypes
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, Dict, Optional

from telethon import Button, TelegramClient, events


@dataclass(frozen=True)
class Config:
    api_id: int
    api_hash: str
    bot_token: str
    chat_id: int


def load_config() -> Config:
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    missing = [name for name, value in {
        "TELEGRAM_API_ID": api_id,
        "TELEGRAM_API_HASH": api_hash,
        "TELEGRAM_BOT_TOKEN": bot_token,
        "TELEGRAM_CHAT_ID": chat_id,
    }.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )

    return Config(
        api_id=int(api_id),
        api_hash=api_hash,
        bot_token=bot_token,
        chat_id=int(chat_id),
    )


def run_command(command: list[str]) -> None:
    subprocess.run(command, check=False, capture_output=True)


def shutdown_now() -> str:
    run_command(["shutdown", "/s", "/t", "0"])
    return "✅ Команда выключения отправлена."


def restart_now() -> str:
    run_command(["shutdown", "/r", "/t", "0"])
    return "✅ Команда перезагрузки отправлена."


def sleep_now() -> str:
    run_command(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
    return "✅ Сон запущен."


def hibernate_now() -> str:
    run_command(["shutdown", "/h"])
    return "✅ Гибернация запущена."


def lock_now() -> str:
    run_command(["rundll32.exe", "user32.dll,LockWorkStation"])
    return "✅ ПК заблокирован."


def screen_off() -> str:
    if sys.platform != "win32":
        return "⚠️ Отключение экрана доступно только на Windows."
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    hwnd = 0xFFFF
    wm_syscommand = 0x0112
    sc_monitorpower = 0xF170
    user32.SendMessageW(hwnd, wm_syscommand, sc_monitorpower, 2)
    return "✅ Экран выключен."


def schedule_shutdown(minutes: int) -> str:
    seconds = max(1, minutes * 60)
    run_command(["shutdown", "/s", "/t", str(seconds)])
    return f"⏲️ Выключение запланировано через {minutes} мин."


def cancel_shutdown() -> str:
    run_command(["shutdown", "/a"])
    return "❎ Таймер выключения отменён."


def require_windows() -> Optional[str]:
    if sys.platform != "win32":
        return "⚠️ Эти команды доступны только на Windows."
    return None


def build_menu() -> list[list[Button]]:
    return [
        [
            Button.inline("😴 Сон", b"sleep"),
            Button.inline("💤 Гибернация", b"hibernate"),
            Button.inline("🔄 Перезагрузка", b"restart"),
        ],
        [
            Button.inline("⛔ Выключение ПК", b"shutdown"),
        ],
        [
            Button.inline("⏲️ Таймер на выключение", b"timer"),
            Button.inline("❌ Отмена таймера", b"cancel_timer"),
        ],
        [
            Button.inline("🔒 Блокировка", b"lock"),
            Button.inline("🌙 Отключить экран", b"screen_off"),
        ],
        [
            Button.inline("📋 Помощь", b"help"),
        ],
    ]


async def main() -> None:
    config = load_config()
    client = TelegramClient("phantom_telethon", config.api_id, config.api_hash)
    await client.start(bot_token=config.bot_token)

    awaiting_timer = {"chat_id": None}

    async def ensure_allowed(event) -> bool:
        if event.chat_id != config.chat_id:
            await event.reply("⛔ Нет доступа.")
            return False
        return True

    async def send_menu(event) -> None:
        await event.respond(
            "Выберите действие:",
            buttons=build_menu(),
        )

    @client.on(events.NewMessage(pattern="/start"))
    async def start_handler(event):
        if not await ensure_allowed(event):
            return
        await send_menu(event)

    @client.on(events.NewMessage(pattern="/help"))
    async def help_handler(event):
        if not await ensure_allowed(event):
            return
        await event.reply(
            "Команды:\n"
            "/shutdown — выключить сейчас\n"
            "/restart — перезагрузить\n"
            "/sleep — сон\n"
            "/hibernate — гибернация\n"
            "/lock — блокировка\n"
            "/screenoff — отключить экран\n"
            "/timer <минуты> — таймер выключения\n"
            "/cancel — отмена таймера"
        )

    @client.on(events.NewMessage(pattern="/shutdown"))
    async def shutdown_handler(event):
        if not await ensure_allowed(event):
            return
        if warning := require_windows():
            await event.reply(warning)
            return
        await event.reply(shutdown_now())

    @client.on(events.NewMessage(pattern="/restart"))
    async def restart_handler(event):
        if not await ensure_allowed(event):
            return
        if warning := require_windows():
            await event.reply(warning)
            return
        await event.reply(restart_now())

    @client.on(events.NewMessage(pattern="/sleep"))
    async def sleep_handler(event):
        if not await ensure_allowed(event):
            return
        if warning := require_windows():
            await event.reply(warning)
            return
        await event.reply(sleep_now())

    @client.on(events.NewMessage(pattern="/hibernate"))
    async def hibernate_handler(event):
        if not await ensure_allowed(event):
            return
        if warning := require_windows():
            await event.reply(warning)
            return
        await event.reply(hibernate_now())

    @client.on(events.NewMessage(pattern="/lock"))
    async def lock_handler(event):
        if not await ensure_allowed(event):
            return
        if warning := require_windows():
            await event.reply(warning)
            return
        await event.reply(lock_now())

    @client.on(events.NewMessage(pattern="/screenoff"))
    async def screenoff_handler(event):
        if not await ensure_allowed(event):
            return
        await event.reply(screen_off())

    @client.on(events.NewMessage(pattern=r"/timer\s+(\d+)"))
    async def timer_handler(event):
        if not await ensure_allowed(event):
            return
        if warning := require_windows():
            await event.reply(warning)
            return
        minutes = int(event.pattern_match.group(1))
        await event.reply(schedule_shutdown(minutes))

    @client.on(events.NewMessage(pattern="/cancel"))
    async def cancel_handler(event):
        if not await ensure_allowed(event):
            return
        if warning := require_windows():
            await event.reply(warning)
            return
        await event.reply(cancel_shutdown())

    @client.on(events.NewMessage)
    async def timer_prompt_handler(event):
        if not await ensure_allowed(event):
            return
        if awaiting_timer["chat_id"] != event.chat_id:
            return
        awaiting_timer["chat_id"] = None
        if not event.raw_text.isdigit():
            await event.reply("Введите количество минут числом.")
            return
        if warning := require_windows():
            await event.reply(warning)
            return
        minutes = int(event.raw_text)
        await event.reply(schedule_shutdown(minutes))

    @client.on(events.CallbackQuery)
    async def callback_handler(event):
        if event.chat_id != config.chat_id:
            await event.answer("Нет доступа.", alert=True)
            return
        action = event.data.decode("utf-8")
        responses: Dict[str, Callable[[], str]] = {
            "shutdown": shutdown_now,
            "restart": restart_now,
            "sleep": sleep_now,
            "hibernate": hibernate_now,
            "lock": lock_now,
            "screen_off": screen_off,
            "cancel_timer": cancel_shutdown,
        }

        if action == "timer":
            awaiting_timer["chat_id"] = event.chat_id
            await event.answer("Введите количество минут.", alert=True)
            return
        if action == "help":
            await event.answer("Смотрите /help", alert=True)
            return

        if warning := require_windows():
            await event.answer(warning, alert=True)
            return

        handler = responses.get(action)
        if handler is None:
            await event.answer("Неизвестная команда.", alert=True)
            return
        message = handler()
        await event.answer(message, alert=True)

    print("Bot started.")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
