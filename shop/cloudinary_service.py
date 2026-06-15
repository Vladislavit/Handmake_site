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

# Ланцюг трансформацій (по кроках): прибрати фон -> тінь -> біле тло -> оптимізація
PRODUCT_TRANSFORMATION = [
    {'effect': 'background_removal'},
    {'effect': 'shadow'},
    {'background': 'white'},
    {'quality': 'auto', 'fetch_format': 'auto'},
]


class CloudinaryUploadError(Exception):
    """Помилка під час завантаження/обробки фото в Cloudinary."""


def is_configured():
    cfg = cloudinary.config()
    return bool(cfg.cloud_name and cfg.api_key and cfg.api_secret)


def upload_product_image(file, folder=PRODUCT_FOLDER):
    """Завантажує файл у Cloudinary з обробкою і повертає secure_url.

    Кидає CloudinaryUploadError у разі проблем (немає ключів, помилка API тощо).
    """
    if not is_configured():
        raise CloudinaryUploadError(
            'Cloudinary не налаштовано: додайте CLOUDINARY_CLOUD_NAME / '
            'CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET у .env'
        )
    try:
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            transformation=PRODUCT_TRANSFORMATION,
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
