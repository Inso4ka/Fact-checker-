import logging
import asyncio
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Bot
from decimal import Decimal

from app.config import config
from app.services.subscriptions import SubscriptionService
from app.services.notifications import NotificationService
from app.clients.perplexity import check_fact
from app.clients.robokassa_client import robokassa_client
from app.db.repositories.payments import PaymentRepository
from app.db.pool import get_pool
from app.utils.text import split_message
from app.utils.notification_cache import is_user_notified, mark_user_notified
from app.utils.crypto import hash_user_id
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
        response += "У вас безграничный доступ ко всем функциям.\n\n"
        response += "Доступные команды:\n"
        response += "• /grant &lt;user_id&gt; &lt;duration&gt; - Выдать подписку\n"
        response += "• /revoke &lt;user_id&gt; - Отозвать подписку\n"
        response += "• /revokeall - Отозвать ВСЕ подписки\n"
        response += "• /hash &lt;user_id&gt; - Получить хеш по ID\n"
        response += "• /mystatus - Проверить свою подписку"
        await message.answer(response, parse_mode="HTML")
    else:
        has_subscription = await SubscriptionService.check_active(user_id)
        
        if has_subscription:
            response += "✅ У вас есть активная подписка.\n"
            response += "Просто отправьте мне любое утверждение, и я проверю его достоверность."
            await message.answer(response, parse_mode="HTML")
        else:
            response += "❌ У вас нет активной подписки.\n\n"
            response += "💳 <b>Выберите тариф для оплаты:</b>"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📅 Месяц - 1000₽", callback_data="pay:1m:1000")],
                [InlineKeyboardButton(text="📅 Полгода - 3600₽", callback_data="pay:6m:3600")],
                [InlineKeyboardButton(text="📅 Год - 6000₽", callback_data="pay:1y:6000")]
            ])
            
            await message.answer(response, reply_markup=keyboard, parse_mode="HTML")


@user_router.callback_query(lambda c: c.data and c.data.startswith("pay:"))
async def process_payment(callback: CallbackQuery):
    """Обработчик выбора тарифа и генерации платежной ссылки"""
    if not callback.data or not callback.from_user:
        return
    
    await callback.answer()
    
    # Парсим callback data: pay:1m:1000
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.message.answer("❌ Ошибка: неверный формат данных")
        return
    
    duration = parts[1]  # 1m, 6m, 1y
    price = int(parts[2])  # 1000, 3600, 6000
    
    user_id = callback.from_user.id
    hashed_id = hash_user_id(user_id, config.hash_salt)
    
    try:
        # Создаем платеж в БД
        pool = get_pool()
        payment_repo = PaymentRepository(pool)
        
        invoice_id = await payment_repo.create_payment(
            user_id=hashed_id,
            amount=Decimal(str(price)),
            duration=duration,
            telegram_user_id=user_id
        )
        
        # Генерируем ссылку для оплаты
        payment_url = robokassa_client.generate_payment_link(
            invoice_id=invoice_id,
            amount=Decimal(str(price)),
            description=f"Подписка на {duration}"
        )
        
        # Красивое отображение тарифа
        duration_text = {
            "1m": "1 месяц",
            "6m": "6 месяцев",
            "1y": "1 год"
        }.get(duration, duration)
        
        # Отправляем ссылку пользователю
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)]
        ])
        
        await callback.message.answer(
            f"💰 <b>Счёт на оплату создан</b>\n\n"
            f"📋 Номер счёта: #{invoice_id}\n"
            f"📅 Тариф: {duration_text}\n"
            f"💵 Сумма: {price}₽\n\n"
            f"Нажмите кнопку ниже для оплаты:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        logger.info(f"Создан платёж #{invoice_id} для пользователя {user_id} ({duration}, {price}₽)")
    
    except Exception as e:
        logger.error(f"Ошибка создания платежа: {e}")
        await callback.message.answer(f"❌ Ошибка при создании счёта: {str(e)}")


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
                f"👤 Администратор: @kroove",
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
    
    # Админ имеет безграничный доступ без проверки подписки
    if not is_admin(user_id):
        has_subscription = await SubscriptionService.check_active(user_id)
        
        if not has_subscription:
            await message.answer(
                f"❌ У вас нет активной подписки.\n\n"
                f"🆔 Ваш ID: <code>{user_id}</code>\n\n"
                f"Отправьте свой ID администратору для получения доступа.\n\n"
                f"👤 Администратор: @kroove",
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
        # Проверяем факт через Perplexity AI
        result = await check_fact(message.text)
        
        # Безопасно удаляем сообщение о загрузке
        try:
            await processing_msg.delete()
        except Exception as del_error:
            logger.warning(f"Не удалось удалить сообщение о загрузке: {del_error}")
        
        # Отправляем результат (с разбивкой на части если длинный)
        chunks = split_message(result)
        for i, chunk in enumerate(chunks):
            try:
                await message.answer(chunk, parse_mode="HTML")
            except Exception as send_error:
                # Если HTML парсинг не сработал, отправляем без парсинга
                logger.error(f"Ошибка отправки с HTML: {send_error}")
                await message.answer(chunk)
            
            if i < len(chunks) - 1:
                await asyncio.sleep(0.1)
    
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        try:
            await processing_msg.delete()
        except:
            pass
        await message.answer(
            f"❌ Произошла ошибка при обработке вашего запроса: {str(e)}"
        )
