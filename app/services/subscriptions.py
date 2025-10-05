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
    async def grant(user_id: int, username: Optional[str], duration: str) -> tuple[bool, Optional[datetime]]:
        """Выдает подписку пользователю"""
        if duration not in SUBSCRIPTION_DURATIONS:
            return False, None
        
        expires_at = datetime.now(timezone.utc) + SUBSCRIPTION_DURATIONS[duration]
        await SubscriptionRepository.create_or_update(user_id, username, expires_at)
        
        return True, expires_at
    
    @staticmethod
    async def revoke(user_id: int) -> bool:
        """Отзывает подписку"""
        return await SubscriptionRepository.delete(user_id)
    
    @staticmethod
    async def get_all_formatted() -> list[SubscriptionInfo]:
        """Получает все подписки с форматированием для отображения"""
        subs = await SubscriptionRepository.get_all()
        result = []
        
        for sub in subs:
            moscow_expires = sub['expires_at'].replace(tzinfo=timezone.utc).astimezone(MOSCOW_TZ)
            moscow_created = sub['created_at'].replace(tzinfo=timezone.utc).astimezone(MOSCOW_TZ)
            
            result.append({
                'user_id': sub['user_id'],
                'username': sub['username'] or "N/A",
                'expires_at_moscow': moscow_expires.strftime("%Y-%m-%d %H:%M"),
                'created_at_moscow': moscow_created.strftime("%Y-%m-%d %H:%M")
            })
        
        return result  # type: ignore
    
    @staticmethod
    async def get_user_subscription(user_id: int) -> Optional[SubscriptionRecord]:
        """Получает подписку конкретного пользователя"""
        return await SubscriptionRepository.get_by_user_id(user_id)
    
    @staticmethod
    async def update_username(user_id: int, username: Optional[str]) -> None:
        """Обновляет username пользователя"""
        await SubscriptionRepository.update_username(user_id, username)
    
    @staticmethod
    def format_duration(duration: str) -> str:
        """Форматирует длительность для отображения"""
        return DURATION_DESCRIPTIONS.get(duration, duration)
    
    @staticmethod
    def format_datetime_moscow(dt: datetime) -> str:
        """Форматирует datetime в московское время"""
        moscow_time = dt.replace(tzinfo=timezone.utc).astimezone(MOSCOW_TZ)
        return moscow_time.strftime("%Y-%m-%d %H:%M")
