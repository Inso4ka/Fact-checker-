import hashlib
import secrets
from typing import Union, Tuple
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


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
    Хеширует user_id с использованием Argon2id + индивидуальная соль + pepper
    
    Защита:
    - Argon2id: медленный алгоритм, защита от GPU brute-force
    - Per-user salt: каждому пользователю своя случайная соль
    - Pepper: глобальный секрет (не в БД)
    
    Args:
        user_id: Telegram user ID
        pepper: Глобальный секрет (HASH_PEPPER из env)
        salt: Индивидуальная соль пользователя (если None - генерируется новая)
    
    Returns:
        Tuple[хеш, соль]
    """
    ph = PasswordHasher(
        time_cost=3,       # Число итераций (баланс скорость/безопасность)
        memory_cost=65536, # 64 MB памяти
        parallelism=4,     # Параллельные потоки
        hash_len=32,       # Длина хеша
        salt_len=16        # Длина соли
    )
    
    # Генерируем новую соль если не передана
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Комбинируем user_id + pepper для хеширования
    data_to_hash = f"{user_id}{pepper}"
    
    # Argon2 внутренне использует соль, но мы храним её явно
    # Это позволяет нам контролировать соль для каждого пользователя
    hash_result = ph.hash(data_to_hash + salt)
    
    return hash_result, salt


def verify_user_id_v2(user_id: Union[int, str], pepper: str, salt: str, stored_hash: str) -> bool:
    """
    Проверяет соответствие user_id сохранённому хешу
    
    Args:
        user_id: Telegram user ID для проверки
        pepper: Глобальный секрет (HASH_PEPPER)
        salt: Индивидуальная соль из БД
        stored_hash: Сохранённый хеш из БД
    
    Returns:
        True если ID соответствует хешу
    """
    ph = PasswordHasher(
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        salt_len=16
    )
    
    data_to_verify = f"{user_id}{pepper}{salt}"
    
    try:
        ph.verify(stored_hash, data_to_verify)
        return True
    except VerifyMismatchError:
        return False
