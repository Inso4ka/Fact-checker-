import os
import logging
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class Config(BaseModel):
    """Конфигурация бота с валидацией"""
    
    telegram_bot_token: str = Field(..., description="Telegram Bot API Token")
    perplexity_api_key: str = Field(..., description="Perplexity AI API Key")
    database_url: str = Field(..., description="PostgreSQL connection URL")
    admin_chat_ids: list[int] = Field(..., description="List of admin Telegram IDs")
    
    log_level: str = Field(default="INFO", description="Logging level")
    
    @field_validator('admin_chat_ids', mode='before')
    @classmethod
    def parse_admin_ids(cls, v):
        """Парсит ADMIN_CHAT_ID из строки в список чисел"""
        if isinstance(v, str):
            return [int(id.strip()) for id in v.split(",")]
        return v
    
    @classmethod
    def from_env(cls) -> "Config":
        """Создает конфиг из переменных окружения с валидацией"""
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        perplexity_key = os.getenv("PERPLEXITY_API_KEY")
        db_url = os.getenv("DATABASE_URL")
        admin_ids = os.getenv("ADMIN_CHAT_ID")
        
        if not telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен")
        if not perplexity_key:
            raise ValueError("PERPLEXITY_API_KEY не установлен")
        if not db_url:
            raise ValueError("DATABASE_URL не установлен")
        if not admin_ids:
            raise ValueError("ADMIN_CHAT_ID не установлен. Укажите один или несколько Telegram ID через запятую")
        
        # Парсим admin_ids через validator
        parsed_ids = cls.parse_admin_ids(admin_ids)
        
        return cls(
            telegram_bot_token=telegram_token,
            perplexity_api_key=perplexity_key,
            database_url=db_url,
            admin_chat_ids=parsed_ids,
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Настраивает логирование для приложения"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


# Глобальный экземпляр конфига
config = Config.from_env()
logger = setup_logging(config.log_level)
