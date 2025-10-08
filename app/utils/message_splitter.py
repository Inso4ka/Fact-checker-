"""Утилиты для разделения сообщений на части"""
import re
from typing import Tuple, Optional


def split_conclusion_and_sources(text: str) -> Tuple[str, Optional[str]]:
    """
    Разделяет текст на вывод и источники
    
    Args:
        text: Полный текст от AI
    
    Returns:
        (conclusion, sources): Кортеж из вывода и источников (или None если нет источников)
    """
    # Ищем заголовок ИСТОЧНИКИ (с HTML тегами или без)
    patterns = [
        r'<b>ИСТОЧНИКИ:</b>',
        r'<b>ИСТОЧНИКИ</b>',
        r'ИСТОЧНИКИ:',
        r'📚\s*ИСТОЧНИКИ:',
        r'📚\s*<b>ИСТОЧНИКИ:</b>',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Разделяем по найденному заголовку
            conclusion = text[:match.start()].strip()
            sources = text[match.start():].strip()
            return conclusion, sources
    
    # Если раздел ИСТОЧНИКИ не найден, возвращаем весь текст как вывод
    return text.strip(), None
