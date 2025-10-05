from datetime import timezone, timedelta

# Московская временная зона (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))

# Длительности подписок
SUBSCRIPTION_DURATIONS = {
    "1m": timedelta(minutes=1),
    "1d": timedelta(days=1),
    "1M": timedelta(days=30),
    "6M": timedelta(days=180),
    "1y": timedelta(days=365)
}

# Описания длительностей для пользователей
DURATION_DESCRIPTIONS = {
    "1m": "1 минуту",
    "1d": "1 день",
    "1M": "1 месяц",
    "6M": "6 месяцев",
    "1y": "1 год"
}

# Лимиты
MAX_MESSAGE_LENGTH = 4096  # Максимальная длина сообщения в Telegram
CLEANUP_INTERVAL_SECONDS = 600  # Интервал очистки подписок (10 минут)
