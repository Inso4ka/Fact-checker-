import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен")
if not PERPLEXITY_API_KEY:
    raise ValueError("PERPLEXITY_API_KEY не установлен")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

perplexity_client = AsyncOpenAI(
    api_key=PERPLEXITY_API_KEY,
    base_url="https://api.perplexity.ai"
)

def load_system_prompt() -> str:
    """Загружает system prompt из файла"""
    try:
        with open("system_prompt.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error("Файл system_prompt.txt не найден")
        raise
    except Exception as e:
        logger.error(f"Ошибка при чтении system_prompt.txt: {e}")
        raise

OSINT_SYSTEM_PROMPT = load_system_prompt()


async def check_fact(user_message: str) -> str:
    try:
        response = await perplexity_client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {"role": "system", "content": OSINT_SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            max_tokens=2000,
            temperature=0.2
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Ошибка при проверке факта: {e}")
        return f"❌ Произошла ошибка при проверке: {str(e)}"


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я бот для проверки фактов.\n\n"
        "Просто отправьте мне любое утверждение, и я проверю его достоверность."
    )


@dp.message()
async def handle_message(message: Message):
    if not message.text:
        return
    
    processing_msg = await message.answer("⏳ Анализирую ваш запрос...")
    
    try:
        result = await check_fact(message.text)
        
        await processing_msg.delete()
        
        if len(result) <= 4096:
            await message.answer(result, parse_mode="HTML")
        else:
            chunks = [result[i:i+4096] for i in range(0, len(result), 4096)]
            for chunk in chunks:
                await message.answer(chunk, parse_mode="HTML")
                await asyncio.sleep(0.1)
    
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        await processing_msg.delete()
        await message.answer(
            f"❌ Произошла ошибка при обработке вашего запроса: {str(e)}"
        )


async def main():
    logger.info("🚀 Запуск fact-checker бота...")
    logger.info(f"✅ Бот инициализирован")
    
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
