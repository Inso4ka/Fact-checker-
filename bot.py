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
ADMIN_USERNAME = "itroyen"
ADMIN_CHAT_ID_ENV = os.getenv("ADMIN_CHAT_ID")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен")
if not PERPLEXITY_API_KEY:
    raise ValueError("PERPLEXITY_API_KEY не установлен")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL не установлен")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

perplexity_client = AsyncOpenAI(
    api_key=PERPLEXITY_API_KEY,
    base_url="https://api.perplexity.ai"
)

db_pool: Optional[asyncpg.Pool] = None
admin_chat_id: Optional[int] = None


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


async def load_admin_chat_id():
    """Загружает admin_chat_id из переменной окружения или базы данных"""
    global admin_chat_id
    
    if ADMIN_CHAT_ID_ENV:
        admin_chat_id = int(ADMIN_CHAT_ID_ENV)
        logger.info(f"✅ Admin chat ID загружен из переменной окружения: {admin_chat_id}")
        await save_admin_chat_id(admin_chat_id)
        return
    
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT value FROM config WHERE key = 'admin_chat_id'"
        )
        if result:
            admin_chat_id = int(result['value'])
            logger.info(f"✅ Admin chat ID загружен из БД: {admin_chat_id}")
        else:
            logger.warning(f"⚠️ Admin chat ID не установлен. Он будет автоматически сохранен при первом сообщении от @{ADMIN_USERNAME}")


async def save_admin_chat_id(chat_id: int):
    """Сохраняет admin_chat_id в базу данных"""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO config (key, value, updated_at)
            VALUES ('admin_chat_id', $1, NOW())
            ON CONFLICT (key)
            DO UPDATE SET value = $1, updated_at = NOW()
            """,
            str(chat_id)
        )
    logger.info(f"✅ Admin chat ID сохранен в БД: {chat_id}")


async def init_db():
    """Инициализирует пул соединений с БД"""
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    logger.info("✅ Подключение к базе данных установлено")
    
    await load_admin_chat_id()


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
    global admin_chat_id
    
    if message.from_user.username == ADMIN_USERNAME and admin_chat_id is None:
        admin_chat_id = message.from_user.id
        await save_admin_chat_id(admin_chat_id)
        logger.info(f"✅ Admin chat ID автоматически обнаружен и сохранен: {admin_chat_id}")
    
    has_subscription = await check_subscription(message.from_user.id)
    
    if has_subscription:
        await message.answer(
            "👋 Привет! Я бот для проверки фактов.\n\n"
            "✅ У вас есть активная подписка.\n"
            "Просто отправьте мне любое утверждение, и я проверю его достоверность."
        )
    else:
        await message.answer(
            "👋 Привет! Я бот для проверки фактов.\n\n"
            "❌ У вас нет активной подписки.\n"
            f"Для получения доступа обратитесь к @{ADMIN_USERNAME}"
        )


@dp.message(Command("grant"))
async def cmd_grant(message: Message):
    global admin_chat_id
    
    if message.from_user.username != ADMIN_USERNAME:
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    if admin_chat_id is None:
        admin_chat_id = message.from_user.id
        await save_admin_chat_id(admin_chat_id)
    
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
    global admin_chat_id
    
    if message.from_user.username != ADMIN_USERNAME:
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    if admin_chat_id is None:
        admin_chat_id = message.from_user.id
        await save_admin_chat_id(admin_chat_id)
    
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
    global admin_chat_id
    
    if message.from_user.username != ADMIN_USERNAME:
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    if admin_chat_id is None:
        admin_chat_id = message.from_user.id
        await save_admin_chat_id(admin_chat_id)
    
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
                f"Для получения доступа обратитесь к @{ADMIN_USERNAME}"
            )
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@dp.message()
async def handle_message(message: Message):
    global admin_chat_id
    
    if not message.text:
        return
    
    if message.from_user.username == ADMIN_USERNAME and admin_chat_id is None:
        admin_chat_id = message.from_user.id
        await save_admin_chat_id(admin_chat_id)
        logger.info(f"✅ Admin chat ID автоматически обнаружен и сохранен: {admin_chat_id}")
    
    has_subscription = await check_subscription(message.from_user.id)
    
    if not has_subscription:
        await message.answer(
            f"❌ У вас нет активной подписки.\n"
            f"Для получения доступа обратитесь к @{ADMIN_USERNAME}\n\n"
            f"Ваш ID: <code>{message.from_user.id}</code>",
            parse_mode="HTML"
        )
        
        if admin_chat_id:
            try:
                username = message.from_user.username or "без username"
                await bot.send_message(
                    admin_chat_id,
                    f"🔔 Новый запрос от пользователя без подписки:\n\n"
                    f"ID: <code>{message.from_user.id}</code>\n"
                    f"Username: @{username}\n"
                    f"Имя: {message.from_user.full_name}\n\n"
                    f"Для выдачи подписки используйте:\n"
                    f"<code>/grant {message.from_user.id} 1M</code>",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить админа: {e}")
        else:
            logger.warning(f"Не могу уведомить админа - admin_chat_id не установлен. Админ должен использовать любую команду (/grant, /revoke, /list)")
        
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
    logger.info(f"👤 Админ: @{ADMIN_USERNAME}")
    
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
