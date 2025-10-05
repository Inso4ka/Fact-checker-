import asyncio
import logging
from aiogram import Bot
from app.db.repositories.subscriptions import SubscriptionRepository
from app.services.notifications import NotificationService
from app.constants import CLEANUP_INTERVAL_SECONDS

logger = logging.getLogger(__name__)


async def subscription_cleanup_task(bot: Bot):
    """Фоновая задача для автоматической очистки истекших подписок"""
    logger.info("🔄 Запущена фоновая задача очистки подписок")
    notification_service = NotificationService(bot)
    
    try:
        while True:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
                
                # Получаем список истекших подписок перед удалением
                expired_subs = await SubscriptionRepository.get_expired()
                
                if expired_subs:
                    # Уведомляем пользователей об истечении подписки
                    for sub in expired_subs:
                        user_id = sub['user_id']
                        success = await notification_service.notify_subscription_expired(user_id)
                        if success:
                            logger.info(f"📬 Пользователь {user_id} уведомлен об истечении подписки")
                    
                    # Удаляем истекшие подписки
                    deleted_count = await SubscriptionRepository.delete_expired()
                    logger.info(f"🗑️ Удалено истекших подписок: {deleted_count}")
            
            except asyncio.CancelledError:
                # Позволяем задаче корректно завершиться при отмене
                logger.info("🛑 Задача очистки подписок остановлена")
                raise
            
            except Exception as e:
                logger.error(f"Ошибка в задаче очистки подписок: {e}")
                # Продолжаем работу даже после ошибки
                await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
    
    except asyncio.CancelledError:
        # Корректная обработка отмены задачи
        logger.info("✅ Задача очистки завершена")
        raise
