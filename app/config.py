import os
import logging
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

# Загружаем переменные из .env файла (для локального запуска)
load_dotenv()


class Config(BaseModel):
    """Конфигурация бота с валидацией"""
    
    telegram_bot_token: str = Field(..., description="Telegram Bot API Token")
    perplexity_api_key: str = Field(..., description="Perplexity AI API Key")
    database_url: str = Field(..., description="PostgreSQL connection URL")
    admin_chat_ids: list[int] = Field(..., description="List of admin Telegram IDs")
    hash_salt: str = Field(..., description="Salt for hashing user IDs")
    
    # Robokassa настройки
    robokassa_merchant_login: str = Field(..., description="Robokassa Merchant Login")
    robokassa_password1: str = Field(..., description="Robokassa Password #1 (for payment links)")
    robokassa_password2: str = Field(..., description="Robokassa Password #2 (for webhooks)")
    robokassa_is_test: bool = Field(default=True, description="Robokassa test mode")
    
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
        hash_salt = os.getenv("HASH_SALT")
        
        # Robokassa параметры
        robokassa_login = os.getenv("ROBOKASSA_MERCHANT_LOGIN")
        robokassa_pass1 = os.getenv("ROBOKASSA_PASSWORD1")
        robokassa_pass2 = os.getenv("ROBOKASSA_PASSWORD2")
        robokassa_test = os.getenv("ROBOKASSA_IS_TEST", "True").lower() == "true"
        
        if not telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен")
        if not perplexity_key:
            raise ValueError("PERPLEXITY_API_KEY не установлен")
        if not db_url:
            raise ValueError("DATABASE_URL не установлен")
        if not admin_ids:
            raise ValueError("ADMIN_CHAT_ID не установлен. Укажите один или несколько Telegram ID через запятую")
        if not hash_salt:
            raise ValueError("HASH_SALT не установлен. Укажите секретную строку для хеширования ID")
        if not robokassa_login:
            raise ValueError("ROBOKASSA_MERCHANT_LOGIN не установлен")
        if not robokassa_pass1:
            raise ValueError("ROBOKASSA_PASSWORD1 не установлен")
        if not robokassa_pass2:
            raise ValueError("ROBOKASSA_PASSWORD2 не установлен")
        
        # Парсим admin_ids через validator
        parsed_ids = cls.parse_admin_ids(admin_ids)
        
        return cls(
            telegram_bot_token=telegram_token,
            perplexity_api_key=perplexity_key,
            database_url=db_url,
            admin_chat_ids=parsed_ids,
            hash_salt=hash_salt,
            robokassa_merchant_login=robokassa_login,
            robokassa_password1=robokassa_pass1,
            robokassa_password2=robokassa_pass2,
            robokassa_is_test=robokassa_test,
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
