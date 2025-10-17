import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiohttp import web

from app.config import config, logger
from app.db.pool import init_pool, close_pool
from app.clients import perplexity
from app.handlers.admin import admin_router
from app.handlers.user import user_router
from app.background.cleanup import subscription_cleanup_task
from app.webhook.robokassa_webhook import create_webhook_app


async def main():
    """Главная функция запуска бота"""
    logger.info("🚀 Запуск fact-checker бота...")
    
    # Инициализация базы данных
    await init_pool(config.database_url)
    
    # Инициализация Perplexity клиента
    perplexity.init_client(config.perplexity_api_key)
    perplexity.load_system_prompt()
    
    # Создание бота и диспетчера
    bot = Bot(token=config.telegram_bot_token)
    dp = Dispatcher()
    
    # Регистрация роутеров (порядок важен: сначала admin, потом user)
    dp.include_router(admin_router)
    dp.include_router(user_router)
    
    # Запуск фоновой задачи очистки подписок с передачей бота для уведомлений
    cleanup_task = asyncio.create_task(subscription_cleanup_task(bot))
    
    # Создание и запуск webhook сервера для Robokassa
    webhook_app = create_webhook_app(bot)
    runner = web.AppRunner(webhook_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 5000)
    await site.start()
    
    logger.info(f"✅ Бот инициализирован")
    logger.info(f"👤 Admin IDs: {', '.join(map(str, config.admin_chat_ids))}")
    logger.info(f"🌐 Webhook сервер запущен на http://0.0.0.0:5000")
    logger.info(f"   - ResultURL: http://your-domain.com/robokassa/result")
    logger.info(f"   - SuccessURL: http://your-domain.com/robokassa/success")
    logger.info(f"   - FailURL: http://your-domain.com/robokassa/fail")
    
    try:
        # Запуск long polling
        await dp.start_polling(bot, skip_updates=True)
    finally:
        # Очистка ресурсов
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        await runner.cleanup()
        await close_pool()
        await bot.session.close()
        logger.info("👋 Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
