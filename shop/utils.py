"""Утиліти: транслітерація українських назв у латинський slug."""
from django.utils.text import slugify

# Спрощена українська транслітерація (для slug, не офіційний стандарт КМУ)
_UA_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'h', 'ґ': 'g', 'д': 'd', 'е': 'e', 'є': 'ie',
    'ж': 'zh', 'з': 'z', 'и': 'y', 'і': 'i', 'ї': 'i', 'й': 'i', 'к': 'k', 'л': 'l',
    'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ь': '', 'ю': 'iu', 'я': 'ia', "'": '', '’': '', 'ʼ': '',
}


def translit_ua(text):
    out = []
    for ch in text:
        rep = _UA_MAP.get(ch.lower())
        out.append(ch if rep is None else rep)
    return ''.join(out)


def ua_slugify(text):
    """Латинський slug з української назви."""
    return slugify(translit_ua(text or ''))


def unique_slugify(instance, value):
    """Унікальний slug у межах моделі (додає -2, -3 за потреби)."""
    base = ua_slugify(value) or 'item'
    model = type(instance)
    slug = base
    i = 2
    while model.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        slug = f'{base}-{i}'
        i += 1
    return slug
