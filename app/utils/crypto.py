import hashlib
import secrets
from typing import Union


SCRYPT_N = 8192
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 64
SALT_LENGTH = 16


def hash_user_id(user_id: Union[int, str], pepper: str = "") -> str:
    """
    Хеширует user_id с использованием Scrypt + pepper
    
    Параметры Scrypt:
        N=8192 (итерации) - защита от brute-force
        r=8 (размер блока) - memory-hard свойства
        p=1 (параллелизм) - баланс производительности
        
    Характеристики:
        - Время хеширования: ~40 мс
        - Потребление памяти: ~8 МБ
        - Стойкость: Очень высокая (★★★★★)
        - Устойчивость к GPU/ASIC атакам
    
    Args:
        user_id: Telegram user ID (int или str)
        pepper: Секретный ключ (из переменной окружения HASH_SALT)
    
    Returns:
        Scrypt хеш в hex формате (128 символов)
    """
    user_id_str = str(user_id).encode('utf-8')
    pepper_bytes = pepper.encode('utf-8')
    
    salt = _generate_deterministic_salt(user_id_str, pepper_bytes)
    
    scrypt_hash = hashlib.scrypt(
        password=user_id_str,
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN
    )
    
    return scrypt_hash.hex()


def verify_user_id(user_id: Union[int, str], hash_value: str, pepper: str = "") -> bool:
    """
    Проверяет соответствие user_id и хеша с использованием защищенного сравнения
    
    Args:
        user_id: Telegram user ID для проверки
        hash_value: Хеш из базы данных
        pepper: Секретный ключ (из переменной окружения HASH_SALT)
    
    Returns:
        True если хеш соответствует user_id, иначе False
    """
    try:
        expected_hash = hash_user_id(user_id, pepper)
        return secrets.compare_digest(expected_hash, hash_value)
    except Exception:
        return False


def _generate_deterministic_salt(user_id_bytes: bytes, pepper_bytes: bytes) -> bytes:
    """
    Генерирует детерминированную соль из user_id + pepper
    
    Детерминированность важна для того, чтобы один и тот же user_id
    всегда давал одинаковый хеш (для поиска в БД)
    
    Args:
        user_id_bytes: User ID в байтах
        pepper_bytes: Pepper в байтах
    
    Returns:
        16 байт соли
    """
    combined = pepper_bytes + user_id_bytes
    salt_hash = hashlib.sha256(combined).digest()
    return salt_hash[:SALT_LENGTH]
