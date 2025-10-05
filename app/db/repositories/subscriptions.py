from datetime import datetime, timezone
from typing import Optional
import asyncpg
import logging
from app.db.pool import get_pool
from app.models.subscription import SubscriptionRecord
from app.utils.crypto import hash_user_id, hash_user_id_v2
from app.config import config

logger = logging.getLogger(__name__)


class SubscriptionRepository:
    """Репозиторий для работы с подписками в БД"""
    
    @staticmethod
    async def check_active(user_id: int) -> bool:
        """Проверяет наличие активной подписки с автоматической миграцией"""
        pool = get_pool()
        
        # Сначала пытаемся найти по новому хешу (Argon2 с солью)
        new_hash, new_salt = hash_user_id_v2(user_id, config.hash_pepper)
        
        async with pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT user_id, salt, expires_at FROM subscriptions WHERE user_id = $1 AND salt IS NOT NULL",
                new_hash
            )
            
            # Если нашли по новому хешу - проверяем срок
            if result:
                expires_at = result['expires_at']
                now_utc_naive = datetime.now(timezone.utc).replace(tzinfo=None)
                return now_utc_naive < expires_at
            
            # Если не нашли по новому - ищем по старому SHA256 хешу (для миграции)
            old_hash = hash_user_id(user_id, config.hash_salt)
            result = await conn.fetchrow(
                "SELECT user_id, salt, expires_at FROM subscriptions WHERE user_id = $1 AND salt IS NULL",
                old_hash
            )
            
            if not result:
                return False
            
            # Нашли старую запись - мигрируем на новый хеш
            expires_at = result['expires_at']
            now_utc_naive = datetime.now(timezone.utc).replace(tzinfo=None)
            
            if now_utc_naive < expires_at:
                # Подписка активна - мигрируем
                logger.info(f"🔄 Миграция пользователя {user_id} с SHA256 на Argon2id")
                await conn.execute(
                    """
                    UPDATE subscriptions 
                    SET user_id = $1, salt = $2 
                    WHERE user_id = $3
                    """,
                    new_hash, new_salt, old_hash
                )
                return True
            
            return False
    
    @staticmethod
    async def create_or_update(
        user_id: int, 
        expires_at: datetime
    ) -> None:
        """Создает или обновляет подписку с новым хешированием"""
        pool = get_pool()
        
        # Используем новый Argon2id хеш
        hashed_id, salt = hash_user_id_v2(user_id, config.hash_pepper)
        
        # Конвертируем в naive UTC datetime для PostgreSQL TIMESTAMP
        naive_expires = expires_at.replace(tzinfo=None) if expires_at.tzinfo else expires_at
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        
        async with pool.acquire() as conn:
            # Сначала удаляем старую SHA256 запись если существует
            old_hash = hash_user_id(user_id, config.hash_salt)
            await conn.execute(
                "DELETE FROM subscriptions WHERE user_id = $1 AND salt IS NULL",
                old_hash
            )
            
            # Вставляем новую Argon2 запись
            await conn.execute(
                """
                INSERT INTO subscriptions (user_id, salt, expires_at, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) 
                DO UPDATE SET expires_at = $3, salt = $2
                """,
                hashed_id, salt, naive_expires, now_naive
            )
    
    @staticmethod
    async def delete(user_id: int) -> bool:
        """Удаляет подписку пользователя (поддерживает оба типа хешей)"""
        pool = get_pool()
        
        # Пытаемся удалить по новому хешу
        new_hash, _ = hash_user_id_v2(user_id, config.hash_pepper)
        
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM subscriptions WHERE user_id = $1",
                new_hash
            )
            
            if result != "DELETE 0":
                return True
            
            # Если не нашли по новому - удаляем по старому
            old_hash = hash_user_id(user_id, config.hash_salt)
            result = await conn.execute(
                "DELETE FROM subscriptions WHERE user_id = $1",
                old_hash
            )
            return result != "DELETE 0"
    
    @staticmethod
    async def get_all() -> list[SubscriptionRecord]:
        """Получает все подписки"""
        pool = get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_id, salt, expires_at, created_at
                FROM subscriptions
                ORDER BY expires_at DESC
                """
            )
            return [dict(row) for row in rows]  # type: ignore
    
    @staticmethod
    async def get_by_user_id(user_id: int) -> Optional[SubscriptionRecord]:
        """Получает подписку по user_id (поддерживает оба типа хешей)"""
        pool = get_pool()
        
        # Пытаемся найти по новому хешу
        new_hash, _ = hash_user_id_v2(user_id, config.hash_pepper)
        
        async with pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT user_id, salt, expires_at, created_at FROM subscriptions WHERE user_id = $1",
                new_hash
            )
            
            if result:
                return dict(result)  # type: ignore
            
            # Если не нашли по новому - ищем по старому
            old_hash = hash_user_id(user_id, config.hash_salt)
            result = await conn.fetchrow(
                "SELECT user_id, salt, expires_at, created_at FROM subscriptions WHERE user_id = $1",
                old_hash
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
                SELECT user_id, salt, expires_at, created_at
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
    
