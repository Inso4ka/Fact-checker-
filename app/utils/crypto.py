import hashlib
from typing import Union


def hash_user_id(user_id: Union[int, str], salt: str = "") -> str:
    """
    Хеширует user_id с использованием SHA256 + соль
    
    Args:
        user_id: Telegram user ID (int или str)
        salt: Соль для хеширования (из переменных окружения)
    
    Returns:
        SHA256 хеш в hex формате
    """
    # Конвертируем в строку и добавляем соль
    data = f"{user_id}{salt}".encode('utf-8')
    
    # Создаем SHA256 хеш
    hash_object = hashlib.sha256(data)
    
    # Возвращаем hex строку
    return hash_object.hexdigest()
