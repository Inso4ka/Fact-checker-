from datetime import datetime
from typing import TypedDict


class SubscriptionRecord(TypedDict):
    """Запись подписки из базы данных"""
    user_id: str  # Argon2id хеш
    salt: str | None  # Индивидуальная соль пользователя (None для старых SHA256 хешей)
    expires_at: datetime
    created_at: datetime


class SubscriptionInfo(TypedDict):
    """Информация о подписке для отображения"""
    user_id: str  # SHA256 хеш
    expires_at_moscow: str
    created_at_moscow: str
