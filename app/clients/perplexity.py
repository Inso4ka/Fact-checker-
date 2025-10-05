import logging
from openai import AsyncOpenAI
from typing import Optional

logger = logging.getLogger(__name__)

_client: Optional[AsyncOpenAI] = None
_system_prompt: Optional[str] = None


def init_client(api_key: str) -> AsyncOpenAI:
    """Инициализирует Perplexity AI клиент"""
    global _client
    _client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.perplexity.ai"
    )
    return _client


def load_system_prompt(file_path: str = "system_prompt.txt") -> str:
    """Загружает system prompt из файла"""
    global _system_prompt
    
    if _system_prompt:
        return _system_prompt
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            _system_prompt = f.read()
            return _system_prompt
    except FileNotFoundError:
        logger.error(f"Файл {file_path} не найден")
        raise
    except Exception as e:
        logger.error(f"Ошибка при чтении {file_path}: {e}")
        raise


async def check_fact(user_message: str) -> str:
    """Проверяет факт через Perplexity AI"""
    if not _client:
        raise RuntimeError("Perplexity client не инициализирован")
    
    if not _system_prompt:
        raise RuntimeError("System prompt не загружен")
    
    try:
        response = await _client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {"role": "system", "content": _system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=2000,
            temperature=0.2
        )
        
        return response.choices[0].message.content or "Нет ответа от AI"
    except Exception as e:
        logger.error(f"Ошибка при проверке факта: {e}")
        return f"❌ Произошла ошибка при проверке: {str(e)}"
