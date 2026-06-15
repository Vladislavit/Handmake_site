from decimal import Decimal

from django.conf import settings

from .models import Product


class Cart:
    """Кошик, що живе в сесії користувача.

    Структура в сесії:
        { "<product_id>:<options>": {"qty": int, "options": str} }
    Один товар із різними опціями (розмір/колір) = різні рядки.
    """

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if cart is None:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    @staticmethod
    def _key(product_id, options=''):
        return f'{product_id}:{options}'

    def add(self, product, qty=1, options='', replace=False):
        key = self._key(product.id, options)
        if key not in self.cart:
            self.cart[key] = {'qty': 0, 'options': options}
        if replace:
            self.cart[key]['qty'] = qty
        else:
            self.cart[key]['qty'] += qty
        self.save()

    def set_qty(self, key, qty):
        if key in self.cart:
            if qty <= 0:
                self.remove(key)
            else:
                self.cart[key]['qty'] = qty
                self.save()

    def remove(self, key):
        if key in self.cart:
            del self.cart[key]
            self.save()

    def clear(self):
        self.session[settings.CART_SESSION_ID] = self.cart = {}
        self.save()

    def save(self):
        self.session.modified = True

    def __iter__(self):
        """Підмішує об'єкти Product і рахує суму кожного рядка."""
        ids = [key.split(':', 1)[0] for key in self.cart]
        products = {str(p.id): p for p in Product.objects.filter(id__in=ids)}
        for key, item in self.cart.items():
            pid = key.split(':', 1)[0]
            product = products.get(pid)
            if product is None:
                continue
            yield {
                'key': key,
                'product': product,
                'options': item['options'],
                'qty': item['qty'],
                'price': product.price,
                'total': product.price * item['qty'],
            }

    def __len__(self):
        return sum(item['qty'] for item in self.cart.values())

    @property
    def subtotal(self):
        return sum(
            (line['total'] for line in self),
            Decimal('0'),
        )

    @property
    def shipping(self):
        if not len(self):
            return Decimal('0')
        if self.subtotal >= settings.FREE_SHIPPING_FROM:
            return Decimal('0')
        return Decimal(settings.SHIPPING_OPTIONS['np-branch'])

    @property
    def total(self):
        return self.subtotal + self.shipping

    @property
    def free_shipping_left(self):
        """Скільки ще додати до безкоштовної доставки (0, якщо вже діє)."""
        left = Decimal(settings.FREE_SHIPPING_FROM) - self.subtotal
        return left if left > 0 else Decimal('0')
