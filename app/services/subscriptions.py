from datetime import datetime, timezone
from typing import Optional
import logging

from app.db.repositories.subscriptions import SubscriptionRepository
from app.constants import SUBSCRIPTION_DURATIONS, MOSCOW_TZ, DURATION_DESCRIPTIONS
from app.models.subscription import SubscriptionRecord, SubscriptionInfo

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Сервис для управления подписками"""
    
    @staticmethod
    async def check_active(user_id: int) -> bool:
        """Проверяет активность подписки"""
        return await SubscriptionRepository.check_active(user_id)
    
    @staticmethod
    async def grant(user_id: int, duration: str) -> tuple[bool, Optional[datetime]]:
        """Выдает подписку пользователю"""
        if duration not in SUBSCRIPTION_DURATIONS:
            return False, None
        
        expires_at = datetime.now(timezone.utc) + SUBSCRIPTION_DURATIONS[duration]
        await SubscriptionRepository.create_or_update(user_id, expires_at)
        
        logger.info(f"✅ Выдана подписка: user_id={user_id}, duration={duration}, expires_at={expires_at}")
        
        return True, expires_at
    
    @staticmethod
    async def revoke(user_id: int) -> bool:
        """Отзывает подписку"""
        return await SubscriptionRepository.delete(user_id)
    
    @staticmethod
    async def revoke_all() -> int:
        """Отзывает ВСЕ подписки, возвращает количество удаленных"""
        count = await SubscriptionRepository.delete_all()
        logger.info(f"🗑️ Отозвано всех подписок: {count}")
        return count
    
    @staticmethod
    async def get_all_formatted() -> list[SubscriptionInfo]:
        """Получает все подписки с форматированием для отображения"""
        subs = await SubscriptionRepository.get_all()
        result = []
        
        for sub in subs:
            # БД возвращает naive datetime (UTC), добавляем timezone и конвертируем в МСК
            expires_utc = sub['expires_at'].replace(tzinfo=timezone.utc)
            created_utc = sub['created_at'].replace(tzinfo=timezone.utc)
            
            moscow_expires = expires_utc.astimezone(MOSCOW_TZ)
            moscow_created = created_utc.astimezone(MOSCOW_TZ)
            
            result.append({
                'user_id': sub['user_id'],
                'expires_at_moscow': moscow_expires.strftime("%Y-%m-%d %H:%M"),
                'created_at_moscow': moscow_created.strftime("%Y-%m-%d %H:%M")
            })
        
        return result  # type: ignore
    
    @staticmethod
    async def get_user_subscription(user_id: int) -> Optional[SubscriptionRecord]:
        """Получает подписку конкретного пользователя"""
        return await SubscriptionRepository.get_by_user_id(user_id)
    
    
    @staticmethod
    def format_duration(duration: str) -> str:
        """Форматирует длительность для отображения"""
        return DURATION_DESCRIPTIONS.get(duration, duration)
    
    @staticmethod
    def format_datetime_moscow(dt: datetime) -> str:
        """Форматирует datetime в московское время"""
        # Если datetime с timezone - конвертируем, если без - считаем UTC
        if dt.tzinfo is None:
            dt_utc = dt.replace(tzinfo=timezone.utc)
        else:
            dt_utc = dt
        
        moscow_time = dt_utc.astimezone(MOSCOW_TZ)
        return moscow_time.strftime("%Y-%m-%d %H:%M")
