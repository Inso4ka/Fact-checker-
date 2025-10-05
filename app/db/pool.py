import asyncpg
from typing import Optional
import logging

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def init_pool(database_url: str) -> asyncpg.Pool:
    """Инициализирует пул соединений с PostgreSQL"""
    global _pool
    _pool = await asyncpg.create_pool(
        database_url, 
        min_size=1, 
        max_size=10,
        command_timeout=60
    )
    logger.info("✅ Подключение к базе данных установлено")
    return _pool


async def close_pool() -> None:
    """Закрывает пул соединений"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("🔒 Соединение с базой данных закрыто")


def get_pool() -> asyncpg.Pool:
    """Получает текущий пул соединений"""
    if _pool is None:
        raise RuntimeError("Database pool не инициализирован")
    return _pool
