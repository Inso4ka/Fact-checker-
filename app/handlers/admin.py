import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import Bot

from app.config import config
from app.services.subscriptions import SubscriptionService
from app.services.notifications import NotificationService
from app.utils.text import split_message
from app.utils.notification_cache import clear_user_notification

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
                "• 1W - 1 неделя\n"
                "• 1M - 1 месяц\n"
                "• 6M - 6 месяцев\n"
                "• 1y - 1 год\n\n"
                "Пример: /grant 123456789 1M"
            )
            return
        
        user_id = int(parts[1])
        duration = parts[2]
        
        success, expires_at = await SubscriptionService.grant(user_id, duration)
        
        if success and expires_at:
            # Очищаем кэш уведомлений - если подписка истечет, админ снова получит уведомление
            clear_user_notification(user_id)
            
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


@admin_router.message(Command("hash"))
async def cmd_hash(message: Message):
    """Команда получения хеша по user_id (только для админов)"""
    if not message.from_user or not message.text:
        return
    
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer(
                "📝 Использование: /hash &lt;user_id&gt;\n\n"
                "Пример: /hash 123456789",
                parse_mode="HTML"
            )
            return
        
        user_id = int(parts[1])
        
        # Получаем подписку пользователя (там будет хеш)
        sub = await SubscriptionService.get_user_subscription(user_id)
        
        if sub:
            await message.answer(
                f"🔐 Хеш для ID <code>{user_id}</code>:\n\n"
                f"<code>{sub['user_id']}</code>",
                parse_mode="HTML"
            )
        else:
            await message.answer(f"❌ Подписка для пользователя {user_id} не найдена")
    
    except ValueError:
        await message.answer("❌ Неверный формат user_id")
    except Exception as e:
        logger.error(f"Ошибка в /hash: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")


@admin_router.message(Command("revokeall"))
async def cmd_revokeall(message: Message):
    """Команда отзыва ВСЕХ подписок (только для админов)"""
    if not message.from_user:
        return
    
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        count = await SubscriptionService.revoke_all()
        
        if count > 0:
            await message.answer(
                f"🗑️ Отозвано всех подписок: {count}\n\n"
                f"Все пользователи потеряли доступ к боту."
            )
        else:
            await message.answer("📋 Нет активных подписок для отзыва")
    
    except Exception as e:
        logger.error(f"Ошибка в /revokeall: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")
