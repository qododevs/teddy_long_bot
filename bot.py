# bot.py
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.utils.chat_action import ChatActionMiddleware
from config import BOT_TOKEN
from db import init_db
from handlers import user, admin

# Настройка логирования
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

async def db_middleware(handler, event, data):
    from db import async_session
    async with async_session() as session:
        data["session"] = session
        return await handler(event, data)

async def main():
    # Проверка токена
    if not BOT_TOKEN or BOT_TOKEN.strip() == "":
        logger.error("❌ BOT_TOKEN не задан в .env! Завершение работы.")
        return

    logger.info("✅ BOT_TOKEN загружен (первые 10 символов): %s...", BOT_TOKEN[:10])

    # Инициализация БД
    try:
        logger.info("🔄 Инициализация базы данных...")
        await init_db()
        logger.info("✅ База данных готова.")
    except Exception as e:
        logger.error("❌ Ошибка инициализации БД: %s", e)
        return

    # Создание бота и диспетчера
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=None))
    dp = Dispatcher()

    # Подключение middleware
    dp.message.middleware(ChatActionMiddleware())
    dp.update.middleware(db_middleware)

    # Подключение роутеров: сначала admin (чтобы админ-клавиатура работала)
    dp.include_router(admin.router)
    dp.include_router(user.router)

    logger.info("🚀 Запуск polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("🛑 Polling остановлен вручную.")
    except Exception as e:
        logger.error("💥 Критическая ошибка в polling: %s", e)

if __name__ == "__main__":
    logger.info("Intialized bot script...")
    try:
        asyncio.run(main())
    except Exception as e:
        logger.critical("🔥 Необработанное исключение на верхнем уровне: %s", e)
        sys.exit(1)