"""Модели для платежей"""
from typing import TypedDict, Optional
from datetime import datetime
from decimal import Decimal


class PaymentRecord(TypedDict):
    """Запись платежа из базы данных"""
    invoice_id: int
    user_id: str  # Scrypt хеш
    amount: Decimal
    duration: str  # 1m, 6m, 1y
    status: str  # pending, paid, failed
    created_at: datetime
    paid_at: Optional[datetime]


class SubscriptionPlan(TypedDict):
    """План подписки"""
    duration: str
    price: int
    label: str
