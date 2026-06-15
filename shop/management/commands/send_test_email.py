"""Надсилає тестовий лист — перевірка налаштувань пошти.

    python manage.py send_test_email
    python manage.py send_test_email --to someone@example.com
"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Надсилає тестовий лист для перевірки SMTP/пошти'

    def add_arguments(self, parser):
        parser.add_argument('--to', default='', help='Кому (інакше — ORDER_NOTIFY_EMAIL)')

    def handle(self, *args, **opts):
        to = opts['to'] or settings.ORDER_NOTIFY_EMAIL
        send_mail(
            'Клубок — тест пошти',
            'Якщо ви це бачите — пошта налаштована правильно. 🧶\n\nКлубок',
            settings.DEFAULT_FROM_EMAIL,
            [to],
            fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Лист надіслано на {to}\nBackend: {settings.EMAIL_BACKEND}'
        ))
