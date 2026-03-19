import asyncio
import logging

import uvicorn
from aiogram import Dispatcher

from notify_bot.api import app as fastapi_app
from notify_bot.bot import bot
from notify_bot.config import API_HOST, API_PORT

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

dp = Dispatcher()


async def main() -> None:
    log.info("Starting ntfy (API on %s:%s)", API_HOST, API_PORT)

    config = uvicorn.Config(
        fastapi_app,
        host=API_HOST,
        port=API_PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)

    try:
        await asyncio.gather(
            server.serve(),
            dp.start_polling(bot),
        )
    finally:
        await bot.session.close()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
