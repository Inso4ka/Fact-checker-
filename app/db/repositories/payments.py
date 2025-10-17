"""Репозиторий для работы с платежами"""
import asyncpg
from typing import Optional
from decimal import Decimal
from datetime import datetime


class PaymentRepository:
    """Репозиторий для работы с платежами"""
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def create_payment(
        self,
        user_id: str,
        amount: Decimal,
        duration: str,
        telegram_user_id: int = None
    ) -> int:
        """
        Создать новый платеж
        
        Args:
            user_id: Хеш ID пользователя
            amount: Сумма платежа
            duration: Длительность подписки (1m, 6m, 1y)
            telegram_user_id: Telegram ID пользователя (для уведомлений)
        
        Returns:
            invoice_id: ID созданного платежа
        """
        async with self.pool.acquire() as conn:
            invoice_id = await conn.fetchval(
                """
                INSERT INTO payments (user_id, amount, duration, status, telegram_user_id)
                VALUES ($1, $2, $3, 'pending', $4)
                RETURNING invoice_id
                """,
                user_id, amount, duration, telegram_user_id
            )
            return invoice_id
    
    async def get_payment(self, invoice_id: int) -> Optional[dict]:
        """Получить платеж по ID"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT invoice_id, user_id, amount, duration, status, created_at, paid_at
                FROM payments
                WHERE invoice_id = $1
                """,
                invoice_id
            )
            return dict(result) if result else None
    
    async def mark_as_paid(self, invoice_id: int) -> None:
        """Отметить платеж как оплаченный"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE payments
                SET status = 'paid', paid_at = CURRENT_TIMESTAMP
                WHERE invoice_id = $1
                """,
                invoice_id
            )
    
    async def mark_as_failed(self, invoice_id: int) -> None:
        """Отметить платеж как неудавшийся"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE payments
                SET status = 'failed'
                WHERE invoice_id = $1
                """,
                invoice_id
            )
    
    async def get_user_payments(self, user_id: str) -> list[dict]:
        """Получить все платежи пользователя"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT invoice_id, user_id, amount, duration, status, created_at, paid_at
                FROM payments
                WHERE user_id = $1
                ORDER BY created_at DESC
                """,
                user_id
            )
            return [dict(row) for row in rows]
