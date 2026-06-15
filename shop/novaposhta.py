"""Тонкий клієнт до API Нової Пошти (v2.0)."""
import json
import time
import urllib.error
import urllib.request

from django.conf import settings


class NovaPoshtaError(Exception):
    pass


def _is_rate_limit(errors):
    text = ' '.join(str(e) for e in errors).lower()
    return 'many request' in text or 'too many' in text or 'limit' in text


def call(model_name, called_method, properties=None, api_key=None, timeout=60,
         retries=6, backoff=2.0):
    payload = {
        'apiKey': api_key or settings.NOVA_POSHTA_API_KEY,
        'modelName': model_name,
        'calledMethod': called_method,
        'methodProperties': properties or {},
    }
    body = json.dumps(payload).encode('utf-8')

    last_error = None
    for attempt in range(retries):
        req = urllib.request.Request(
            settings.NOVA_POSHTA_API_URL,
            data=body,
            headers={'Content-Type': 'application/json'},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.load(resp)
        except urllib.error.URLError as exc:
            last_error = f'Помилка зʼєднання з НП: {exc}'
            time.sleep(backoff * (attempt + 1))
            continue

        if data.get('success'):
            return data.get('data', []), data.get('info', {})

        errors = data.get('errors') or data.get('warnings') or ['невідома помилка']
        # Ліміт частоти — почекати й повторити
        if _is_rate_limit(errors):
            last_error = '; '.join(str(e) for e in errors)
            time.sleep(backoff * (attempt + 1))
            continue
        raise NovaPoshtaError('; '.join(str(e) for e in errors))

    raise NovaPoshtaError(f'Не вдалося після {retries} спроб: {last_error}')


def get_warehouses(page=1, limit=500, city_ref='', city_name=''):
    props = {'Page': str(page), 'Limit': str(limit)}
    if city_ref:
        props['CityRef'] = city_ref
    if city_name:
        props['CityName'] = city_name
    return call('Address', 'getWarehouses', props)
