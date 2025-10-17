"""Webhook сервер для обработки уведомлений от Robokassa"""
import logging
from aiohttp import web
from app.clients.robokassa_client import RobokassaClient
from app.db.repositories.payments import PaymentRepository
from app.db.pool import get_pool
from app.services.subscriptions import SubscriptionService
from app.config import config
from aiogram import Bot

logger = logging.getLogger(__name__)


async def handle_result_url(request: web.Request) -> web.Response:
    """
    Обработчик ResultURL - webhook от Robokassa о успешной оплате
    
    Robokassa отправляет:
    - OutSum: сумма платежа
    - InvId: ID платежа (invoice_id)
    - SignatureValue: подпись для проверки
    """
    # Получаем данные из POST или GET запроса
    data = await request.post() if request.method == 'POST' else request.query
    
    out_sum = data.get('OutSum', '')
    inv_id = data.get('InvId', '')
    signature = data.get('SignatureValue', '')
    
    logger.info(f"Получен webhook от Robokassa: InvId={inv_id}, OutSum={out_sum}")
    
    # Проверяем подпись
    if not RobokassaClient.verify_signature(out_sum, inv_id, signature):
        logger.error(f"Неверная подпись webhook: InvId={inv_id}")
        return web.Response(text=f"bad sign", status=400)
    
    try:
        invoice_id = int(inv_id)
        
        # Получаем платеж из БД
        pool = get_pool()
        payment_repo = PaymentRepository(pool)
        payment = await payment_repo.get_payment(invoice_id)
        
        if not payment:
            logger.error(f"Платеж #{invoice_id} не найден в БД")
            return web.Response(text=f"OK{inv_id}", status=200)
        
        # Проверяем, не был ли уже обработан
        if payment['status'] == 'paid':
            logger.info(f"Платеж #{invoice_id} уже обработан")
            return web.Response(text=f"OK{inv_id}", status=200)
        
        # Отмечаем платеж как оплаченный
        await payment_repo.mark_as_paid(invoice_id)
        
        # Выдаем подписку пользователю
        duration = payment['duration']
        user_hashed_id = payment['user_id']
        
        # Определяем длительность подписки
        duration_mapping = {
            '1m': '1M',
            '6m': '6M',
            '1y': '1y'
        }
        subscription_duration = duration_mapping.get(duration, '1M')
        
        # Создаем подписку
        expires_at = await SubscriptionService.grant_subscription(
            user_hashed_id,
            subscription_duration
        )
        
        logger.info(f"✅ Подписка выдана для платежа #{invoice_id} (хеш: {user_hashed_id[:16]}..., до {expires_at})")
        
        # Отправляем уведомление пользователю
        bot: Bot = request.app['bot']
        telegram_user_id = payment.get('telegram_user_id')
        
        if telegram_user_id:
            duration_text = {
                "1m": "1 месяц",
                "6m": "6 месяцев",
                "1y": "1 год"
            }.get(duration, duration)
            
            try:
                await bot.send_message(
                    chat_id=telegram_user_id,
                    text=f"✅ <b>Оплата успешно принята!</b>\n\n"
                         f"📋 Номер счёта: #{invoice_id}\n"
                         f"📅 Подписка: {duration_text}\n"
                         f"💵 Сумма: {out_sum}₽\n\n"
                         f"Ваша подписка активирована до {expires_at.strftime('%Y-%m-%d %H:%M')} (МСК)",
                    parse_mode="HTML"
                )
                logger.info(f"📨 Уведомление о платеже #{invoice_id} отправлено пользователю {telegram_user_id}")
            except Exception as notify_error:
                logger.error(f"Ошибка отправки уведомления пользователю {telegram_user_id}: {notify_error}")
        
        logger.info(f"💰 Оплата успешно обработана для платежа #{invoice_id}")
        
        # Возвращаем обязательный ответ Robokassa
        return web.Response(text=f"OK{inv_id}", status=200)
    
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}")
        return web.Response(text=f"OK{inv_id}", status=200)


async def handle_success_url(request: web.Request) -> web.Response:
    """Обработчик SuccessURL - редирект после успешной оплаты"""
    inv_id = request.query.get('InvId', 'неизвестно')
    return web.Response(
        text=f"✅ Оплата прошла успешно! Номер счёта: #{inv_id}. Подписка активирована.",
        content_type='text/html; charset=utf-8'
    )


async def handle_fail_url(request: web.Request) -> web.Response:
    """Обработчик FailURL - редирект после неудачной оплаты"""
    return web.Response(
        text="❌ Оплата не прошла. Попробуйте снова.",
        content_type='text/html; charset=utf-8'
    )


def create_webhook_app(bot: Bot) -> web.Application:
    """Создает aiohttp приложение для webhook"""
    app = web.Application()
    app['bot'] = bot
    
    app.router.add_route('*', '/robokassa/result', handle_result_url)
    app.router.add_route('*', '/robokassa/success', handle_success_url)
    app.router.add_route('*', '/robokassa/fail', handle_fail_url)
    
    return app
