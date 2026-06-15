from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .cart import Cart
from .emails import send_order_emails
from .forms import CheckoutForm
from .models import Category, NPCity, NPWarehouse, Order, OrderItem, Product


def _to_int(value, default=1):
    """Безпечний розбір числа з форми (без 500 на сміттєвому вводі)."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

# Сортування лістингу (значення select -> orderby)
SORTS = {
    'popular': ('-reviews_count', '-rating'),
    'cheap': ('price',),
    'expensive': ('-price',),
    'new': ('-created',),
}

WORLD_META = {
    Category.KIND_TOY: {
        'title': 'Іграшки',
        'eyebrow': 'Для найменших',
        'description': 'М\'які в\'язані друзі з натуральної бавовни — зайчики, котики, '
                       'лисички та погримушки. Безпечні й приємні на дотик.',
    },
    Category.KIND_HOME: {
        'title': 'Кашпо',
        'eyebrow': 'Для вашого дому',
        'description': 'Підвісні макраме, плетені кошики й кашпо на ланцюжку — '
                       'ручне плетіння з натуральної бавовни та джуту для ваших рослин.',
    },
}


def _sorted(qs, request):
    sort = request.GET.get('sort', 'popular')
    return qs.order_by(*SORTS.get(sort, SORTS['popular'])), sort


def _filters_for_kind(kind):
    # Декоративні чіпи-фільтри (як у прототипі)
    if kind == Category.KIND_HOME:
        return ['Усі', 'Підвісні', 'Плетені', 'На ланцюжку', 'Великі']
    return ['Усі', 'Маленькі', 'Великі', 'Новинки', 'В наявності']


def home(request):
    categories = Category.objects.filter(is_visible=True)
    return render(request, 'shop/index.html', {
        'toy_categories': [c for c in categories if c.kind == Category.KIND_TOY],
        'home_categories': [c for c in categories if c.kind == Category.KIND_HOME],
        'categories_count': len(categories),
    })


def world(request, kind):
    if kind not in WORLD_META:
        raise Http404()
    products, sort = _sorted(Product.objects.filter(category__kind=kind), request)
    meta = WORLD_META[kind]
    return render(request, 'shop/listing.html', {
        'page_title': meta['title'],
        'eyebrow': meta['eyebrow'],
        'description': meta['description'],
        'crumbs': [('Головна', '/'), (meta['title'], None)],
        'products': products,
        'count': products.count(),
        'sort': sort,
        'theme_home': kind == Category.KIND_HOME,
        'filters': _filters_for_kind(kind),
    })


def category(request, slug):
    cat = get_object_or_404(Category, slug=slug, is_visible=True)
    products, sort = _sorted(cat.products.all(), request)
    world_title = WORLD_META[cat.kind]['title']
    return render(request, 'shop/listing.html', {
        'page_title': cat.name,
        'eyebrow': cat.eyebrow or WORLD_META[cat.kind]['eyebrow'],
        'description': cat.description,
        'crumbs': [('Головна', '/'), (world_title, f'/catalog/{cat.kind}/'), (cat.name, None)],
        'products': products,
        'count': products.count(),
        'sort': sort,
        'theme_home': cat.is_home,
        'filters': _filters_for_kind(cat.kind),
    })


def product(request, slug):
    prod = get_object_or_404(Product, slug=slug)
    related = prod.category.products.exclude(id=prod.id)[:4]
    world_title = WORLD_META[prod.category.kind]['title']
    return render(request, 'shop/product.html', {
        'product': prod,
        'related': related,
        'theme_home': prod.category.is_home,
        'crumbs': [
            ('Головна', '/'),
            (world_title, f'/catalog/{prod.category.kind}/'),
            (prod.category.name, prod.category.get_absolute_url()),
            (prod.name, None),
        ],
    })


# --------------------------- Кошик ---------------------------

def cart_detail(request):
    return render(request, 'shop/cart.html', {})


@require_POST
def cart_add(request, product_id):
    prod = get_object_or_404(Product, id=product_id)
    if prod.is_coming_soon or not prod.is_available:
        messages.info(request, 'Цей товар поки недоступний.')
        return redirect(prod.get_absolute_url())
    cart = Cart(request)
    qty = max(1, _to_int(request.POST.get('qty'), 1))
    parts = [p for p in (request.POST.get('size', ''), request.POST.get('color', '')) if p]
    options = ' · '.join(parts)
    cart.add(prod, qty=qty, options=options)
    messages.success(request, f'«{prod.name}» додано в кошик')
    if request.POST.get('next') == 'cart':
        return redirect('shop:cart')
    return redirect(prod.get_absolute_url())


@require_POST
def cart_update(request, key):
    cart = Cart(request)
    cart.set_qty(key, _to_int(request.POST.get('qty'), 1))
    return redirect('shop:cart')


@require_POST
def cart_remove(request, key):
    Cart(request).remove(key)
    return redirect('shop:cart')


# --------------------------- Оформлення ---------------------------

def checkout(request):
    cart = Cart(request)
    if not len(cart):
        return redirect('shop:cart')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                # Доставка за обраним методом; безкоштовно при перевищенні порога
                if cart.subtotal >= settings.FREE_SHIPPING_FROM:
                    order.shipping = 0
                else:
                    order.shipping = settings.SHIPPING_OPTIONS.get(order.delivery, 0)
                order.total = cart.subtotal + order.shipping
                order.save()
                for line in cart:
                    OrderItem.objects.create(
                        order=order,
                        product=line['product'],
                        name=line['product'].name,
                        options=line['options'],
                        price=line['price'],
                        qty=line['qty'],
                    )
            cart.clear()
            # Листи: підтвердження покупцю + сповіщення власнику (збій не зриває заказ)
            send_order_emails(order)
            # Запамʼятовуємо замовлення в сесії — щоб сторінку подяки
            # бачив лише той, хто його щойно оформив (захист від IDOR).
            request.session['last_order_id'] = order.id
            return redirect('shop:checkout_done', order_id=order.id)
    else:
        form = CheckoutForm()

    return render(request, 'shop/checkout.html', {'form': form})


def checkout_done(request, order_id):
    # Деталі замовлення (ПІБ, телефон, адреса) показуємо лише власнику сесії.
    if request.session.get('last_order_id') != order_id:
        raise Http404()
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'shop/checkout_done.html', {'order': order})


# --------------------------- Нова Пошта (JSON з БД) ---------------------------

def np_cities(request):
    """Автодоповнення міст: /np/cities/?q=оде"""
    q = request.GET.get('q', '').strip()
    qs = NPCity.objects.all()
    if q:
        qs = qs.filter(name__istartswith=q)
    else:
        qs = qs.none()
    cities = [
        {'ref': c.ref, 'name': c.name, 'area': c.area}
        for c in qs[:15]
    ]
    return JsonResponse({'cities': cities})


def np_warehouses(request):
    """Відділення міста: /np/warehouses/?city=<ref>&type=branch|poshtomat"""
    city_ref = request.GET.get('city', '').strip()
    wtype = request.GET.get('type', '').strip()
    qs = NPWarehouse.objects.filter(city__ref=city_ref) if city_ref else NPWarehouse.objects.none()
    if wtype == 'branch':
        qs = qs.filter(is_poshtomat=False)
    elif wtype == 'poshtomat':
        qs = qs.filter(is_poshtomat=True)
    warehouses = [
        {
            'ref': w.ref,
            'number': w.number,
            'description': w.description,
            'short_address': w.short_address,
            'is_poshtomat': w.is_poshtomat,
            'lat': w.lat,
            'lng': w.lng,
        }
        for w in qs[:500]
    ]
    return JsonResponse({'warehouses': warehouses})
