"""Завантаження фото товарів у Cloudinary з ШІ-обробкою.

Трансформації (застосовуються під час завантаження, результат — готовий secure_url):
    e_background_removal — вбудоване ШІ-видалення фону Cloudinary;
    e_shadow            — реалістична падаюча тінь;
    b_white             — білий фон замість прозорого;
    q_auto, f_auto      — автооптимізація якості та формату.
"""
import logging

import cloudinary
import cloudinary.uploader

logger = logging.getLogger(__name__)

PRODUCT_FOLDER = 'klubok/products'

# Повна обробка (по кроках):
#   1) прибрати фон (об'єкт на прозорому);
#   2) trim — обрізати прозорі поля до меж об'єкта (поки фон прозорий!);
#   3) тінь;
#   4) fit — вписати об'єкт зі збереженням пропорцій (з полями);
#   5) pad до квадрата з білим тлом -> об'єкт автоматично по центру;
#   6) оптимізація якості/формату.
PRODUCT_TRANSFORMATION = [
    {'effect': 'background_removal'},
    {'effect': 'trim'},
    {'effect': 'shadow'},
    {'width': 880, 'height': 880, 'crop': 'fit'},
    {'width': 1000, 'height': 1000, 'crop': 'pad', 'background': 'white'},
    {'quality': 'auto', 'fetch_format': 'auto'},
]

# «Як є»: без зміни вигляду, лише веб-оптимізація розміру/формату
OPTIMIZE_ONLY = [
    {'quality': 'auto', 'fetch_format': 'auto'},
]


class CloudinaryUploadError(Exception):
    """Помилка під час завантаження/обробки фото в Cloudinary."""


def is_configured():
    cfg = cloudinary.config()
    return bool(cfg.cloud_name and cfg.api_key and cfg.api_secret)


def upload_product_image(file, folder=PRODUCT_FOLDER, process=True):
    """Завантажує файл у Cloudinary і повертає secure_url.

    process=True  — повна обробка (фон/тінь/біле тло/квадрат);
    process=False — лишити як є (тільки веб-оптимізація).

    Кидає CloudinaryUploadError у разі проблем (немає ключів, помилка API тощо).
    """
    if not is_configured():
        raise CloudinaryUploadError(
            'Cloudinary не налаштовано: додайте CLOUDINARY_CLOUD_NAME / '
            'CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET у .env'
        )
    transformation = PRODUCT_TRANSFORMATION if process else OPTIMIZE_ONLY
    try:
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            transformation=transformation,
            resource_type='image',
        )
    except cloudinary.exceptions.Error as exc:
        logger.exception('Cloudinary API error')
        raise CloudinaryUploadError(f'Помилка Cloudinary API: {exc}') from exc
    except Exception as exc:  # мережа, таймаут, несподіване
        logger.exception('Cloudinary upload failed')
        raise CloudinaryUploadError(f'Не вдалося завантажити фото: {exc}') from exc

    secure_url = result.get('secure_url')
    if not secure_url:
        raise CloudinaryUploadError('Cloudinary не повернув secure_url')
    return secure_url
