from datetime import datetime
from typing import TypedDict, Optional


class SubscriptionRecord(TypedDict):
    """Запись подписки из базы данных"""
    user_id: int
    username: Optional[str]
    expires_at: datetime
    created_at: datetime


class SubscriptionInfo(TypedDict):
    """Информация о подписке для отображения"""
    user_id: int
    username: str
    expires_at_moscow: str
    created_at_moscow: str
