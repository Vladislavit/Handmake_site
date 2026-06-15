"""Завантажує відділення та поштомати Нової Пошти в базу.

Приклади:
    python manage.py sync_novaposhta                 # усі по Україні
    python manage.py sync_novaposhta --city "Одеса"  # лише одне місто
    python manage.py sync_novaposhta --limit 500 --max-pages 3
"""
import time

from django.core.management.base import BaseCommand
from django.db import transaction

from shop import novaposhta
from shop.models import NPCity, NPWarehouse


def _coord(value):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if f != 0 else None


class Command(BaseCommand):
    help = 'Синхронізує міста та відділення/поштомати Нової Пошти в БД'

    def add_arguments(self, parser):
        parser.add_argument('--city', default='', help='Назва міста (інакше — вся Україна)')
        parser.add_argument('--limit', type=int, default=500, help='Розмір сторінки (макс. 500)')
        parser.add_argument('--max-pages', type=int, default=0, help='Обмежити кількість сторінок (0 = без ліміту)')
        parser.add_argument('--delay', type=float, default=0.6, help='Пауза між сторінками, сек (проти ліміту НП)')

    def handle(self, *args, **opts):
        city_name = opts['city']
        limit = max(1, min(opts['limit'], 500))
        max_pages = opts['max_pages']
        delay = opts['delay']

        cities = {c.ref: c for c in NPCity.objects.all()}
        total = created = updated = 0
        page = 1

        while True:
            self.stdout.write(f'Сторінка {page}…', ending=' ')
            rows, info = novaposhta.get_warehouses(page=page, limit=limit, city_name=city_name)
            if not rows:
                self.stdout.write('порожньо.')
                break

            with transaction.atomic():
                for w in rows:
                    city_ref = w.get('CityRef')
                    if not city_ref:
                        continue
                    city = cities.get(city_ref)
                    if city is None:
                        city, _ = NPCity.objects.update_or_create(
                            ref=city_ref,
                            defaults={
                                'name': w.get('CityDescription', ''),
                                'area': w.get('SettlementAreaDescription', '')
                                        or w.get('AreaDescription', ''),
                            },
                        )
                        cities[city_ref] = city

                    category = w.get('CategoryOfWarehouse', '') or ''
                    _, was_created = NPWarehouse.objects.update_or_create(
                        ref=w['Ref'],
                        defaults={
                            'city': city,
                            'number': w.get('Number', ''),
                            'description': w.get('Description', ''),
                            'short_address': w.get('ShortAddress', ''),
                            'category': category,
                            'is_poshtomat': category.lower() == 'postomat',
                            'lat': _coord(w.get('Latitude')),
                            'lng': _coord(w.get('Longitude')),
                        },
                    )
                    total += 1
                    created += was_created
                    updated += not was_created

            self.stdout.write(f'оброблено {len(rows)} (всього {total}).')
            page += 1
            if max_pages and page > max_pages:
                break
            if delay:
                time.sleep(delay)

        self.stdout.write(self.style.SUCCESS(
            f'Готово. Відділень: {total} (нових {created}, оновлено {updated}); '
            f'міст у БД: {len(cities)}.'
        ))
