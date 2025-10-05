import hashlib
import secrets
from typing import Union, Tuple
from argon2 import Type
from argon2.low_level import hash_secret_raw
import base64


def hash_user_id(user_id: Union[int, str], salt: str = "") -> str:
    """
    Хеширует user_id с использованием SHA256 + соль (УСТАРЕЛО - для миграции)
    
    Args:
        user_id: Telegram user ID (int или str)
        salt: Соль для хеширования (из переменных окружения)
    
    Returns:
        SHA256 хеш в hex формате
    """
    data = f"{user_id}{salt}".encode('utf-8')
    hash_object = hashlib.sha256(data)
    return hash_object.hexdigest()


def hash_user_id_v2(user_id: Union[int, str], pepper: str, salt: str | None = None) -> Tuple[str, str]:
    """
    Хеширует user_id с использованием Argon2id (полностью детерминированно)
    
    Защита:
    - Argon2id: медленный алгоритм, защита от GPU brute-force
    - Детерминированная соль: вычисляется из user_id + pepper через HMAC
    - Pepper: глобальный секрет (не в БД)
    - Для одного ID всегда один хеш (детерминированность)
    
    Args:
        user_id: Telegram user ID
        pepper: Глобальный секрет (HASH_PEPPER из env)
        salt: НЕ ИСПОЛЬЗУЕТСЯ (для обратной совместимости API)
    
    Returns:
        Tuple[хеш (base64), соль (hex)]
    """
    # Генерируем детерминированную соль из user_id + pepper
    # Используем HMAC-SHA256 для создания уникальной, но воспроизводимой соли
    import hmac
    salt_data = f"{user_id}".encode('utf-8')
    pepper_key = pepper.encode('utf-8')
    salt_hmac = hmac.new(pepper_key, salt_data, hashlib.sha256).digest()
    salt_bytes = salt_hmac[:16]  # Первые 16 байт
    
    # Конвертируем в hex для возврата
    salt_hex = salt_bytes.hex()
    
    # Комбинируем user_id + pepper для хеширования
    data_to_hash = f"{user_id}{pepper}".encode('utf-8')
    
    # Используем low-level API с детерминированной солью
    hash_bytes = hash_secret_raw(
        secret=data_to_hash,
        salt=salt_bytes,
        time_cost=3,        # Число итераций
        memory_cost=65536,  # 64 MB памяти
        parallelism=4,      # Параллельные потоки
        hash_len=32,        # 32 байта хеш
        type=Type.ID        # Argon2id
    )
    
    # Конвертируем в base64 для хранения
    hash_b64 = base64.b64encode(hash_bytes).decode('utf-8')
    
    return hash_b64, salt_hex


def verify_user_id_v2(user_id: Union[int, str], pepper: str, salt: str, stored_hash: str) -> bool:
    """
    Проверяет соответствие user_id сохранённому хешу
    
    Args:
        user_id: Telegram user ID для проверки
        pepper: Глобальный секрет (HASH_PEPPER)
        salt: НЕ ИСПОЛЬЗУЕТСЯ (соль детерминированная)
        stored_hash: Сохранённый хеш из БД (base64)
    
    Returns:
        True если ID соответствует хешу
    """
    # Пересчитываем хеш (соль детерминированная, вычисляется внутри)
    recalculated_hash, _ = hash_user_id_v2(user_id, pepper)
    
    # Сравниваем хеши
    return recalculated_hash == stored_hash
