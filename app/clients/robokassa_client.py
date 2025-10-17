"""Клиент для работы с Robokassa"""
import hashlib
from decimal import Decimal
from robokassa import HashAlgorithm, Robokassa
from app.config import config


class RobokassaClient:
    """Клиент для генерации платежных ссылок Robokassa"""
    
    def __init__(self):
        self.robokassa = Robokassa(
            merchant_login=config.robokassa_merchant_login,
            password1=config.robokassa_password1,
            password2=config.robokassa_password2,
            is_test=config.robokassa_is_test,
            algorithm=HashAlgorithm.md5
        )
    
    def generate_payment_link(
        self,
        invoice_id: int,
        amount: Decimal,
        description: str = "Подписка на бота"
    ) -> str:
        """
        Генерирует платежную ссылку
        
        Args:
            invoice_id: ID платежа
            amount: Сумма платежа
            description: Описание платежа
        
        Returns:
            URL для оплаты
        """
        payment_url = self.robokassa.generate_open_payment_link(
            out_sum=float(amount),
            inv_id=invoice_id,
            description=description
        )
        return str(payment_url)
    
    @staticmethod
    def verify_signature(
        out_sum: str,
        inv_id: str,
        signature: str
    ) -> bool:
        """
        Проверяет подпись от Robokassa
        
        Args:
            out_sum: Сумма платежа
            inv_id: ID платежа
            signature: Подпись от Robokassa
        
        Returns:
            True если подпись верна
        """
        # Формат подписи: md5(OutSum:InvId:Password2)
        signature_string = f"{out_sum}:{inv_id}:{config.robokassa_password2}"
        expected_signature = hashlib.md5(signature_string.encode()).hexdigest().upper()
        return signature.upper() == expected_signature


# Глобальный экземпляр клиента
robokassa_client = RobokassaClient()
