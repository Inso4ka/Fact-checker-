import logging
import asyncio
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import Bot

from app.config import config
from app.services.subscriptions import SubscriptionService
from app.services.notifications import NotificationService
from app.clients.perplexity import check_fact
from app.utils.text import split_message
from app.utils.notification_cache import is_user_notified, mark_user_notified
from app.constants import MOSCOW_TZ
from datetime import timezone

logger = logging.getLogger(__name__)

user_router = Router()


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in config.admin_chat_ids


@user_router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start - приветствие и информация о боте"""
    if not message.from_user:
        return
    
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
        has_subscription = await SubscriptionService.check_active(user_id)
        
        if has_subscription:
            response += "✅ У вас есть активная подписка.\n"
            response += "Просто отправьте мне любое утверждение, и я проверю его достоверность."
        else:
            response += "❌ У вас нет активной подписки.\n"
            response += f"Для получения доступа отправьте свой ID администратору.\n\n"
            response += "👤 Администраторы: @itroyen, @JaffarUgerr\n\n"
            response += "Команды:\n"
            response += "• /mystatus - Проверить статус подписки"
    
    await message.answer(response, parse_mode="HTML")


@user_router.message(Command("mystatus"))
async def cmd_mystatus(message: Message):
    """Команда проверки статуса подписки"""
    if not message.from_user:
        return
    
    try:
        sub = await SubscriptionService.get_user_subscription(message.from_user.id)
        
        if sub:
            # БД возвращает naive datetime (UTC), конвертируем в московское время
            expires_utc = sub['expires_at'].replace(tzinfo=timezone.utc)
            moscow_time = expires_utc.astimezone(MOSCOW_TZ)
            expires = moscow_time.strftime("%Y-%m-%d %H:%M")
            await message.answer(
                f"✅ У вас есть активная подписка\n"
                f"📅 Действует до: {expires} (МСК)"
            )
        else:
            await message.answer(
                f"❌ У вас нет активной подписки\n"
                f"🆔 Ваш ID: <code>{message.from_user.id}</code>\n\n"
                f"Отправьте свой ID администратору для получения доступа.\n\n"
                f"👤 Администраторы: @itroyen, @JaffarUgerr",
                parse_mode="HTML"
            )
    
    except Exception as e:
        logger.error(f"Ошибка в /mystatus: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")


@user_router.message()
async def handle_message(message: Message, bot: Bot):
    """Обработчик всех текстовых сообщений"""
    if not message.text or not message.from_user:
        return
    
    user_id = message.from_user.id
    has_subscription = await SubscriptionService.check_active(user_id)
    
    if not has_subscription:
        await message.answer(
            f"❌ У вас нет активной подписки.\n\n"
            f"🆔 Ваш ID: <code>{user_id}</code>\n\n"
            f"Отправьте свой ID администратору для получения доступа.\n\n"
            f"👤 Администраторы: @itroyen, @JaffarUgerr",
            parse_mode="HTML"
        )
        
        # Уведомляем админов о новом пользователе ТОЛЬКО ОДИН РАЗ
        # Защита от спама незарегистрированных пользователей
        if not is_user_notified(user_id):
            mark_user_notified(user_id)
            
            notification_service = NotificationService(bot)
            await notification_service.notify_admins_new_user(
                config.admin_chat_ids,
                user_id,
                message.from_user.username or "без username",
                message.from_user.full_name or "Unknown"
            )
            logger.info(f"📢 Отправлено уведомление админам о новом пользователе {user_id}")
        
        return
    
    processing_msg = await message.answer("⏳ Анализирую ваш запрос...")
    
    try:
        # Обновляем username пользователя
        await SubscriptionService.update_username(user_id, message.from_user.username or None)
        
        # Проверяем факт через Perplexity AI
        result = await check_fact(message.text)
        
        await processing_msg.delete()
        
        # Отправляем результат (с разбивкой на части если длинный)
        chunks = split_message(result)
        for i, chunk in enumerate(chunks):
            await message.answer(chunk, parse_mode="HTML")
            if i < len(chunks) - 1:
                await asyncio.sleep(0.1)
    
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        await processing_msg.delete()
        await message.answer(
            f"❌ Произошла ошибка при обработке вашего запроса: {str(e)}"
        )
