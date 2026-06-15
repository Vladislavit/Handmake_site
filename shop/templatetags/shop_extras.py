from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


# --- SVG-«балванки» з прототипу (показуємо, доки немає завантаженого фото) ---

def _bunny(c1, c2):
    return f'''<svg viewBox="0 0 120 120" fill="none">
  <ellipse cx="60" cy="108" rx="32" ry="5" fill="{c2}" opacity=".22"/>
  <path d="M44 42c-6-22 0-30 6-30s12 8 6 30" fill="#fff" stroke="{c2}" stroke-width="2.4"/>
  <path d="M76 42c6-22 0-30-6-30s-12 8-6 30" fill="#fff" stroke="{c2}" stroke-width="2.4"/>
  <path d="M48 36c-3-14 0-19 3-19" stroke="{c1}" stroke-width="3" stroke-linecap="round"/>
  <path d="M72 36c3-14 0-19-3-19" stroke="{c1}" stroke-width="3" stroke-linecap="round"/>
  <circle cx="60" cy="64" r="30" fill="#fff" stroke="{c2}" stroke-width="2.4"/>
  <circle cx="51" cy="60" r="3" fill="{c2}"/><circle cx="69" cy="60" r="3" fill="{c2}"/>
  <path d="M56 70c2 3 6 3 8 0" stroke="{c2}" stroke-width="2.2" stroke-linecap="round"/>
  <circle cx="60" cy="67" r="2.6" fill="{c1}"/></svg>'''


def _hanging(c):
    return f'''<svg viewBox="0 0 120 120" fill="none">
  <path d="M60 6v12" stroke="{c}" stroke-width="2.4" stroke-linecap="round"/>
  <circle cx="60" cy="20" r="3" stroke="{c}" stroke-width="2"/>
  <path d="M60 23c-16 6-22 18-22 30M60 23c16 6 22 18 22 30M60 23c-7 8-7 24 0 30M60 23c7 8 7 24 0 30" stroke="{c}" stroke-width="2" stroke-dasharray="2 5"/>
  <path d="M40 56h40l-5 34a7 7 0 0 1-7 6H52a7 7 0 0 1-7-6l-5-34Z" fill="#fff" stroke="{c}" stroke-width="2.6"/>
  <path d="M60 56c-7-16-2-30 0-34 2 4 7 18 0 34Z" fill="#7C8A63"/>
  <path d="M60 52c-12-7-19-2-22 0 7 5 17 5 22 0ZM60 52c12-7 19-2 22 0-7 5-17 5-22 0Z" fill="#7C8A63"/></svg>'''


def _woven(c):
    return f'''<svg viewBox="0 0 120 120" fill="none">
  <path d="M34 44h52l-6 44a8 8 0 0 1-8 7H48a8 8 0 0 1-8-7l-6-44Z" fill="#fff" stroke="{c}" stroke-width="2.6"/>
  <path d="M37 56h46M39 70h42M41 84h38" stroke="{c}" stroke-width="1.8"/>
  <path d="M60 44c-8-18-2-30 0-34 2 4 8 16 0 34Z" fill="#7C8A63"/>
  <path d="M60 40c-13-7-20-2-23 0 7 5 18 5 23 0ZM60 40c13-7 20-2 23 0-7 5-18 5-23 0Z" fill="#7C8A63"/></svg>'''


def _chain(c):
    return f'''<svg viewBox="0 0 120 120" fill="none">
  <circle cx="60" cy="10" r="4" stroke="{c}" stroke-width="2"/>
  <circle cx="60" cy="20" r="4" stroke="{c}" stroke-width="2"/>
  <circle cx="60" cy="30" r="4" stroke="{c}" stroke-width="2"/>
  <path d="M40 44h40l-5 34a7 7 0 0 1-7 6H52a7 7 0 0 1-7-6l-5-34Z" fill="#fff" stroke="{c}" stroke-width="2.6"/>
  <path d="M40 44c8 4 32 4 40 0" stroke="{c}" stroke-width="2"/>
  <path d="M60 44c-7-16-2-28 0-32 2 4 7 16 0 32Z" fill="#7C8A63"/></svg>'''


def _placeholder_svg(product):
    kind = product.placeholder
    c1 = product.color1 or '#C5806C'
    c2 = product.color2 or '#A4604D'
    if kind == 'hanging':
        return _hanging(c2)
    if kind == 'woven':
        return _woven(c2)
    if kind == 'chain':
        return _chain(c2)
    return _bunny(c1, c2)


@register.simple_tag
def product_media(product):
    """Фото товару (Cloudinary), або декоративна SVG-балванка, якщо фото ще немає."""
    url = product.main_image_url
    if url:
        alt = escape(product.name)
        return mark_safe(f'<img class="media-photo" src="{escape(url)}" alt="{alt}" loading="lazy">')
    return mark_safe(_placeholder_svg(product))


@register.simple_tag
def placeholder_svg(product):
    """Лише SVG-балванка (для мініатюр галереї тощо)."""
    return mark_safe(_placeholder_svg(product))


@register.filter
def uah(value):
    """Форматує ціну як у прототипі: «540 ₴»."""
    try:
        return f'{int(value)} ₴'
    except (TypeError, ValueError):
        return value
