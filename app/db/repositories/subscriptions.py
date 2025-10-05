from datetime import datetime, timezone
from typing import Optional
import asyncpg
from app.db.pool import get_pool
from app.models.subscription import SubscriptionRecord
from app.utils.crypto import hash_user_id
from app.config import config


class SubscriptionRepository:
    """Репозиторий для работы с подписками в БД"""
    
    @staticmethod
    async def check_active(user_id: int) -> bool:
        """Проверяет наличие активной подписки"""
        pool = get_pool()
        hashed_id = hash_user_id(user_id, config.hash_salt)
        
        async with pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT expires_at FROM subscriptions WHERE user_id = $1",
                hashed_id
            )
            
            if not result:
                return False
            
            # БД возвращает naive datetime (UTC), сравниваем с naive UTC
            expires_at = result['expires_at']
            now_utc_naive = datetime.now(timezone.utc).replace(tzinfo=None)
            return now_utc_naive < expires_at
    
    @staticmethod
    async def create_or_update(
        user_id: int, 
        expires_at: datetime
    ) -> None:
        """Создает или обновляет подписку"""
        pool = get_pool()
        hashed_id = hash_user_id(user_id, config.hash_salt)
        
        # Конвертируем в naive UTC datetime для PostgreSQL TIMESTAMP
        naive_expires = expires_at.replace(tzinfo=None) if expires_at.tzinfo else expires_at
        # created_at тоже берем из Python, чтобы синхронизировать время
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO subscriptions (user_id, expires_at, created_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) 
                DO UPDATE SET expires_at = $2
                """,
                hashed_id, naive_expires, now_naive
            )
    
    @staticmethod
    async def delete(user_id: int) -> bool:
        """Удаляет подписку пользователя"""
        pool = get_pool()
        hashed_id = hash_user_id(user_id, config.hash_salt)
        
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM subscriptions WHERE user_id = $1",
                hashed_id
            )
            return result != "DELETE 0"
    
    @staticmethod
    async def get_all() -> list[SubscriptionRecord]:
        """Получает все подписки"""
        pool = get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_id, expires_at, created_at
                FROM subscriptions
                ORDER BY expires_at DESC
                """
            )
            return [dict(row) for row in rows]  # type: ignore
    
    @staticmethod
    async def get_by_user_id(user_id: int) -> Optional[SubscriptionRecord]:
        """Получает подписку по user_id"""
        pool = get_pool()
        hashed_id = hash_user_id(user_id, config.hash_salt)
        
        async with pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT user_id, expires_at, created_at FROM subscriptions WHERE user_id = $1",
                hashed_id
            )
            return dict(result) if result else None  # type: ignore
    
    @staticmethod
    async def get_expired() -> list[SubscriptionRecord]:
        """Получает список истекших подписок перед удалением"""
        pool = get_pool()
        now_utc_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_id, expires_at, created_at
                FROM subscriptions
                WHERE expires_at < $1
                """,
                now_utc_naive
            )
            return [dict(row) for row in rows]  # type: ignore
    
    @staticmethod
    async def delete_expired() -> int:
        """Удаляет истекшие подписки, возвращает количество удаленных"""
        pool = get_pool()
        # Используем naive UTC datetime для PostgreSQL
        now_utc_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM subscriptions WHERE expires_at < $1",
                now_utc_naive
            )
            
            if result == "DELETE 0":
                return 0
            
            # Извлекаем число из "DELETE N"
            count = int(result.split()[-1])
            return count
    
