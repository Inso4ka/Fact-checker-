"""
Кэш для отслеживания уведомлений админам о новых пользователях.
Защита от спама незарегистрированных пользователей.
"""

# Кэш пользователей, которым уже отправили уведомление админу
_notified_users: set[int] = set()


def is_user_notified(user_id: int) -> bool:
    """Проверяет, было ли уже отправлено уведомление о пользователе"""
    return user_id in _notified_users


def mark_user_notified(user_id: int) -> None:
    """Отмечает, что пользователю отправлено уведомление"""
    _notified_users.add(user_id)


def clear_user_notification(user_id: int) -> None:
    """Очищает статус уведомления для пользователя (при выдаче подписки)"""
    _notified_users.discard(user_id)


def get_notified_count() -> int:
    """Возвращает количество пользователей в кэше уведомлений"""
    return len(_notified_users)
