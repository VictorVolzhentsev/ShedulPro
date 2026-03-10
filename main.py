import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import StateFilter

import config
from database import db
import urfu_api
import notifications
from handlers import base_router, schedule_router, group_selection_router

# Logging setup
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Bot and dispatcher initialization
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Fallback router for unknown messages (must be included LAST)
from aiogram import Router
fallback_router = Router()

@fallback_router.message(StateFilter(None))
async def fallback_handler(message: types.Message):
    user_data = await db.get_user_settings(message.from_user.id)
    if user_data:
        lang = user_data['language']
        text = "Не понимаю. Используйте кнопки меню или /help" if lang == "ru" else "I don't understand. Use menu buttons or /help"
        await message.answer(text)
    else:
        await message.answer("Используйте /start для начала / Use /start to begin")

# Register routers in correct priority order
dp.include_routers(base_router, group_selection_router, schedule_router, fallback_router)

async def on_startup(dispatcher: Dispatcher):
    # Initialize connection to DB
    await db.connect()
    logging.info("Database connected")
    notifications.start_scheduler(bot, db)
    logging.info("Notification scheduler started")


async def on_shutdown(bot: Bot):
    notifications.stop_scheduler()
    await urfu_api.close_session()
    await db.close()
    logging.info("Bot session closed")


async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
