import asyncio
import logging
from app.db.repositories.subscriptions import SubscriptionRepository
from app.constants import CLEANUP_INTERVAL_SECONDS

logger = logging.getLogger(__name__)


async def subscription_cleanup_task():
    """Фоновая задача для автоматической очистки истекших подписок"""
    logger.info("🔄 Запущена фоновая задача очистки подписок")
    
    try:
        while True:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
                
                deleted_count = await SubscriptionRepository.delete_expired()
                
                if deleted_count > 0:
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
