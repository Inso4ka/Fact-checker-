import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import Bot

from app.config import config
from app.services.subscriptions import SubscriptionService
from app.services.notifications import NotificationService
from app.utils.text import split_message

logger = logging.getLogger(__name__)

admin_router = Router()


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in config.admin_chat_ids


@admin_router.message(Command("grant"))
async def cmd_grant(message: Message, bot: Bot):
    """Команда выдачи подписки (только для админов)"""
    if not message.from_user or not message.text:
        return
    
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
        
        success, expires_at = await SubscriptionService.grant(user_id, None, duration)
        
        if success and expires_at:
            await message.answer(
                f"✅ Подписка успешно выдана пользователю {user_id} на период {duration}"
            )
            
            # Уведомляем пользователя
            notification_service = NotificationService(bot)
            await notification_service.notify_subscription_granted(user_id, duration, expires_at)
        else:
            await message.answer("❌ Неверный период подписки")
    
    except ValueError:
        await message.answer("❌ Неверный формат user_id")
    except Exception as e:
        logger.error(f"Ошибка в /grant: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")


@admin_router.message(Command("revoke"))
async def cmd_revoke(message: Message, bot: Bot):
    """Команда отзыва подписки (только для админов)"""
    if not message.from_user or not message.text:
        return
    
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
        success = await SubscriptionService.revoke(user_id)
        
        if success:
            await message.answer(f"✅ Подписка отозвана у пользователя {user_id}")
            
            # Уведомляем пользователя
            notification_service = NotificationService(bot)
            await notification_service.notify_subscription_revoked(user_id)
        else:
            await message.answer("❌ Подписка не найдена")
    
    except ValueError:
        await message.answer("❌ Неверный формат user_id")
    except Exception as e:
        logger.error(f"Ошибка в /revoke: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")


@admin_router.message(Command("list"))
async def cmd_list(message: Message):
    """Команда просмотра всех подписок (только для админов)"""
    if not message.from_user:
        return
    
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        subs = await SubscriptionService.get_all_formatted()
        
        if not subs:
            await message.answer("📋 Нет активных подписок")
            return
        
        text = "📋 <b>Активные подписки:</b>\n\n"
        
        for sub in subs:
            text += f"👤 ID: <code>{sub['user_id']}</code>\n"
            text += f"   Username: @{sub['username']}\n"
            text += f"   Создана: {sub['created_at_moscow']}\n"
            text += f"   Истекает: {sub['expires_at_moscow']}\n\n"
        
        # Разбиваем на части если длинное
        chunks = split_message(text)
        for chunk in chunks:
            await message.answer(chunk, parse_mode="HTML")
    
    except Exception as e:
        logger.error(f"Ошибка в /list: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")
