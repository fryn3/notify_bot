from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession

from notify_bot.config import BOT_TOKEN, CHAT_ID, PROXY

_session = AiohttpSession(proxy=PROXY) if PROXY else None
bot = Bot(token=BOT_TOKEN, session=_session)


async def send_notification(text: str, parse_mode: str | None = None) -> None:
    await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode=parse_mode)
