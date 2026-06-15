"""Надсилання листів про замовлення (покупцю + власнику магазину)."""
import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_order_emails(order):
    """Лист-підтвердження покупцю та сповіщення власнику.

    Помилки надсилання не валять оформлення — лише логуються.
    """
    ctx = {'order': order, 'items': list(order.items.all())}
    num = f'{order.id:05d}'

    # 1) Покупцю (якщо лишив email)
    if order.email:
        try:
            body = render_to_string('email/order_customer.txt', ctx)
            EmailMessage(
                subject=f'Клубок — замовлення №{num} прийнято',
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[order.email],
            ).send(fail_silently=False)
        except Exception:
            logger.exception('Не вдалося надіслати лист покупцю для замовлення %s', order.id)

    # 2) Власнику магазину
    if settings.ORDER_NOTIFY_EMAIL:
        try:
            body = render_to_string('email/order_owner.txt', ctx)
            EmailMessage(
                subject=f'🧶 Нове замовлення №{num} — {order.total} ₴',
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.ORDER_NOTIFY_EMAIL],
                reply_to=[order.email] if order.email else None,
            ).send(fail_silently=False)
        except Exception:
            logger.exception('Не вдалося надіслати сповіщення власнику для замовлення %s', order.id)
