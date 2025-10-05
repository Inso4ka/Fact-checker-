import logging
from datetime import datetime
from typing import Optional
from aiogram import Bot
from app.services.subscriptions import SubscriptionService

logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис для отправки уведомлений пользователям"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def notify_subscription_granted(
        self, 
        user_id: int, 
        duration: str, 
        expires_at: datetime
    ) -> bool:
        """Уведомляет пользователя о выдаче подписки"""
        try:
            duration_text = SubscriptionService.format_duration(duration)
            expires_str = SubscriptionService.format_datetime_moscow(expires_at)
            
            await self.bot.send_message(
                user_id,
                f"🎉 Вам выдана подписка на бота!\n\n"
                f"⏰ Срок: {duration_text}\n"
                f"📅 Действует до: {expires_str} (МСК)\n\n"
                f"Теперь вы можете отправлять мне любые утверждения для проверки фактов."
            )
            return True
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")
            return False
    
    async def notify_subscription_revoked(self, user_id: int) -> bool:
        """Уведомляет пользователя об отзыве подписки"""
        try:
            await self.bot.send_message(
                user_id,
                f"❌ Ваша подписка на бота была отозвана.\n\n"
                f"Для продления доступа обратитесь к администратору."
            )
            return True
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")
            return False
    
    async def notify_admins_new_user(
        self, 
        admin_ids: list[int], 
        user_id: int, 
        username: str, 
        full_name: str
    ) -> None:
        """Уведомляет админов о новом пользователе без подписки"""
        for admin_id in admin_ids:
            try:
                await self.bot.send_message(
                    admin_id,
                    f"🔔 Новый запрос от пользователя без подписки:\n\n"
                    f"ID: <code>{user_id}</code>\n"
                    f"Username: @{username}\n"
                    f"Имя: {full_name}\n\n"
                    f"Для выдачи подписки используйте:\n"
                    f"<code>/grant {user_id} 1M</code>",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить админа {admin_id}: {e}")
    
    
    async def notify_admins_subscription_expired(
        self, 
        admin_ids: list[int], 
        user_id_hash: str
    ) -> None:
        """Уведомляет админов об истечении подписки пользователя"""
        for admin_id in admin_ids:
            try:
                await self.bot.send_message(
                    admin_id,
                    f"⏰ Подписка пользователя истекла:\n\n"
                    f"ID Hash: <code>{user_id_hash[:16]}...</code>\n\n"
                    f"Запросите у пользователя его ID для продления.",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить админа {admin_id} об истечении подписки: {e}")
