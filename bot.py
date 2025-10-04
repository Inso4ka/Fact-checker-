import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from openai import AsyncOpenAI
import asyncpg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_CHAT_IDS_STR = os.getenv("ADMIN_CHAT_ID")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен")
if not PERPLEXITY_API_KEY:
    raise ValueError("PERPLEXITY_API_KEY не установлен")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL не установлен")
if not ADMIN_CHAT_IDS_STR:
    raise ValueError("ADMIN_CHAT_ID не установлен. Укажите один или несколько Telegram ID через запятую")

ADMIN_CHAT_IDS = [int(id.strip()) for id in ADMIN_CHAT_IDS_STR.split(",")]

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

perplexity_client = AsyncOpenAI(
    api_key=PERPLEXITY_API_KEY,
    base_url="https://api.perplexity.ai"
)

db_pool: Optional[asyncpg.Pool] = None


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


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь админом"""
    return user_id in ADMIN_CHAT_IDS


async def init_db():
    """Инициализирует пул соединений с БД"""
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    logger.info("✅ Подключение к базе данных установлено")


async def close_db():
    """Закрывает пул соединений"""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("🔒 Соединение с базой данных закрыто")


async def check_subscription(user_id: int) -> bool:
    """Проверяет наличие активной подписки у пользователя"""
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT expires_at FROM subscriptions WHERE user_id = $1",
            user_id
        )
        
        if not result:
            return False
        
        expires_at = result['expires_at']
        return datetime.now() < expires_at


async def grant_subscription(user_id: int, username: Optional[str], duration: str) -> bool:
    """Выдаёт подписку пользователю"""
    durations = {
        "1m": timedelta(minutes=1),
        "1d": timedelta(days=1),
        "1M": timedelta(days=30),
        "6M": timedelta(days=180),
        "1y": timedelta(days=365)
    }
    
    if duration not in durations:
        return False
    
    expires_at = datetime.now() + durations[duration]
    
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO subscriptions (user_id, username, expires_at)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) 
            DO UPDATE SET expires_at = $3, username = $2
            """,
            user_id, username, expires_at
        )
    
    return True


async def revoke_subscription(user_id: int) -> bool:
    """Отбирает подписку у пользователя"""
    async with db_pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM subscriptions WHERE user_id = $1",
            user_id
        )
        return result != "DELETE 0"


async def list_subscriptions() -> list:
    """Возвращает список всех активных подписок"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT user_id, username, expires_at, created_at
            FROM subscriptions
            ORDER BY expires_at DESC
            """
        )
        return [dict(row) for row in rows]


async def cleanup_expired_subscriptions():
    """Удаляет истекшие подписки"""
    async with db_pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM subscriptions WHERE expires_at < $1",
            datetime.now()
        )
        if result != "DELETE 0":
            logger.info(f"🗑️ Удалены истекшие подписки: {result}")


async def subscription_cleanup_task():
    """Фоновая задача для очистки истекших подписок каждые 10 минут"""
    while True:
        try:
            await asyncio.sleep(600)
            await cleanup_expired_subscriptions()
        except Exception as e:
            logger.error(f"Ошибка в задаче очистки подписок: {e}")


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
    user_id = message.from_user.id
    
    response = f"👋 Привет! Я бот для проверки фактов.\n\n"
    response += f"🆔 Ваш Telegram ID: <code>{user_id}</code>\n\n"
    
    if is_admin(user_id):
        response += "👑 Вы администратор бота.\n\n"
        response += "Доступные команды:\n"
        response += "• /grant <user_id> <duration> - Выдать подписку\n"
        response += "• /revoke <user_id> - Отозвать подписку\n"
        response += "• /list - Список подписок\n"
        response += "• /mystatus - Проверить свою подписку"
    else:
        has_subscription = await check_subscription(user_id)
        
        if has_subscription:
            response += "✅ У вас есть активная подписка.\n"
            response += "Просто отправьте мне любое утверждение, и я проверю его достоверность."
        else:
            response += "❌ У вас нет активной подписки.\n"
            response += f"Для получения доступа отправьте свой ID администратору.\n\n"
            response += "Команды:\n"
            response += "• /mystatus - Проверить статус подписки"
    
    await message.answer(response, parse_mode="HTML")


@dp.message(Command("grant"))
async def cmd_grant(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            await message.answer(
                "📝 Использование: /grant <user_id> <duration>\n\n"
                "Доступные периоды:\n"
                "• 1m - 1 минута\n"
                "• 1d - 1 день\n"
                "• 1M - 1 месяц\n"
                "• 6M - 6 месяцев\n"
                "• 1y - 1 год\n\n"
                "Пример: /grant 123456789 1M"
            )
            return
        
        user_id = int(parts[1])
        duration = parts[2]
        
        success = await grant_subscription(user_id, None, duration)
        
        if success:
            await message.answer(f"✅ Подписка успешно выдана пользователю {user_id} на период {duration}")
        else:
            await message.answer("❌ Неверный период подписки")
    
    except ValueError:
        await message.answer("❌ Неверный формат user_id")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("revoke"))
async def cmd_revoke(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer(
                "📝 Использование: /revoke <user_id>\n\n"
                "Пример: /revoke 123456789"
            )
            return
        
        user_id = int(parts[1])
        success = await revoke_subscription(user_id)
        
        if success:
            await message.answer(f"✅ Подписка отозвана у пользователя {user_id}")
        else:
            await message.answer("❌ Подписка не найдена")
    
    except ValueError:
        await message.answer("❌ Неверный формат user_id")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("list"))
async def cmd_list(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        subs = await list_subscriptions()
        
        if not subs:
            await message.answer("📋 Нет активных подписок")
            return
        
        text = "📋 <b>Активные подписки:</b>\n\n"
        
        for sub in subs:
            user_id = sub['user_id']
            username = sub['username'] or "N/A"
            expires = sub['expires_at'].strftime("%Y-%m-%d %H:%M")
            created = sub['created_at'].strftime("%Y-%m-%d %H:%M")
            
            text += f"👤 ID: <code>{user_id}</code>\n"
            text += f"   Username: @{username}\n"
            text += f"   Создана: {created}\n"
            text += f"   Истекает: {expires}\n\n"
        
        if len(text) > 4096:
            chunks = [text[i:i+4096] for i in range(0, len(text), 4096)]
            for chunk in chunks:
                await message.answer(chunk, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("mystatus"))
async def cmd_mystatus(message: Message):
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT expires_at FROM subscriptions WHERE user_id = $1",
                message.from_user.id
            )
        
        if result:
            expires = result['expires_at'].strftime("%Y-%m-%d %H:%M")
            await message.answer(
                f"✅ У вас есть активная подписка\n"
                f"📅 Действует до: {expires}"
            )
        else:
            await message.answer(
                f"❌ У вас нет активной подписки\n"
                f"🆔 Ваш ID: <code>{message.from_user.id}</code>\n\n"
                f"Отправьте свой ID администратору для получения доступа.",
                parse_mode="HTML"
            )
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@dp.message()
async def handle_message(message: Message):
    if not message.text:
        return
    
    has_subscription = await check_subscription(message.from_user.id)
    
    if not has_subscription:
        await message.answer(
            f"❌ У вас нет активной подписки.\n\n"
            f"🆔 Ваш ID: <code>{message.from_user.id}</code>\n\n"
            f"Отправьте свой ID администратору для получения доступа.",
            parse_mode="HTML"
        )
        
        for admin_id in ADMIN_CHAT_IDS:
            try:
                username = message.from_user.username or "без username"
                await bot.send_message(
                    admin_id,
                    f"🔔 Новый запрос от пользователя без подписки:\n\n"
                    f"ID: <code>{message.from_user.id}</code>\n"
                    f"Username: @{username}\n"
                    f"Имя: {message.from_user.full_name}\n\n"
                    f"Для выдачи подписки используйте:\n"
                    f"<code>/grant {message.from_user.id} 1M</code>",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить админа {admin_id}: {e}")
        
        return
    
    processing_msg = await message.answer("⏳ Анализирую ваш запрос...")
    
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO subscriptions (user_id, username, expires_at, created_at)
                VALUES ($1, $2, (SELECT expires_at FROM subscriptions WHERE user_id = $1), NOW())
                ON CONFLICT (user_id) 
                DO UPDATE SET username = $2
                """,
                message.from_user.id,
                message.from_user.username
            )
        
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
    
    await init_db()
    
    asyncio.create_task(subscription_cleanup_task())
    
    logger.info(f"✅ Бот инициализирован")
    logger.info(f"👤 Admin IDs: {', '.join(map(str, ADMIN_CHAT_IDS))}")
    
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
