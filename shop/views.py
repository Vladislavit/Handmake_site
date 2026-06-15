from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

PER_PAGE = 12

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


# Робочі чіпи-фільтри для категорії/пошуку
REFINE_OPTIONS = [
    ('', 'Усі'),
    ('available', 'В наявності'),
    ('new', 'Новинки'),
    ('sale', 'Зі знижкою'),
]


def _apply_refine(qs, f):
    if f == 'available':
        return qs.filter(is_available=True, is_coming_soon=False)
    if f == 'new':
        return qs.filter(badge='Новинка')
    if f == 'sale':
        return qs.filter(old_price__isnull=False, old_price__gt=F('price'))
    return qs


def _build_chips(request, param, options):
    """Список чіпів-посилань; зберігає інші параметри (sort, q), скидає page."""
    current = request.GET.get(param, '')
    chips = []
    for value, label in options:
        params = request.GET.copy()
        params.pop('page', None)
        if value:
            params[param] = value
        else:
            params.pop(param, None)
        encoded = params.urlencode()
        chips.append({
            'label': label,
            'href': request.path + ('?' + encoded if encoded else ''),
            'active': current == value,
        })
    return chips


def _listing_response(request, products, *, page_title, eyebrow, description,
                      crumbs, theme_home, chips, search_q=''):
    products = _apply_refine(products, request.GET.get('f', ''))
    products, sort = _sorted(products, request)
    paginator = Paginator(products, PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    params = request.GET.copy()
    params.pop('page', None)
    encoded = params.urlencode()

    return render(request, 'shop/listing.html', {
        'page_title': page_title,
        'eyebrow': eyebrow,
        'description': description,
        'crumbs': crumbs,
        'page_obj': page_obj,
        'count': paginator.count,
        'sort': sort,
        'theme_home': theme_home,
        'chips': chips,
        'search_q': search_q,
        'qs_prefix': (encoded + '&') if encoded else '',
    })


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
    meta = WORLD_META[kind]
    cats = Category.objects.filter(kind=kind, is_visible=True)
    products = Product.objects.filter(category__kind=kind)

    cat_slug = request.GET.get('cat', '')
    if cat_slug:
        products = products.filter(category__slug=cat_slug)

    chips = _build_chips(request, 'cat', [('', 'Усі')] + [(c.slug, c.name) for c in cats])
    return _listing_response(
        request, products,
        page_title=meta['title'], eyebrow=meta['eyebrow'], description=meta['description'],
        crumbs=[('Головна', '/'), (meta['title'], None)],
        theme_home=(kind == Category.KIND_HOME), chips=chips,
    )


def category(request, slug):
    cat = get_object_or_404(Category, slug=slug, is_visible=True)
    world_title = WORLD_META[cat.kind]['title']
    chips = _build_chips(request, 'f', REFINE_OPTIONS)
    return _listing_response(
        request, cat.products.all(),
        page_title=cat.name, eyebrow=cat.eyebrow or WORLD_META[cat.kind]['eyebrow'],
        description=cat.description,
        crumbs=[('Головна', '/'), (world_title, f'/catalog/{cat.kind}/'), (cat.name, None)],
        theme_home=cat.is_home, chips=chips,
    )


def search(request):
    q = request.GET.get('q', '').strip()
    products = Product.objects.none()
    if q:
        products = Product.objects.filter(
            Q(name__icontains=q) | Q(meta__icontains=q)
            | Q(description__icontains=q) | Q(category__name__icontains=q)
        ).distinct()
    chips = _build_chips(request, 'f', REFINE_OPTIONS) if q else []
    return _listing_response(
        request, products,
        page_title=f'Пошук: «{q}»' if q else 'Пошук',
        eyebrow='Результати пошуку',
        description='' if q else 'Введіть запит у полі пошуку вгорі.',
        crumbs=[('Головна', '/'), ('Пошук', None)],
        theme_home=False, chips=chips, search_q=q,
    )


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

@ratelimit(key='ip', rate='8/h', method='POST', block=True)
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


# --------------------------- SEO ---------------------------

def sitemap_xml(request):
    base = request.build_absolute_uri('/').rstrip('/')
    locs = [base + '/', base + '/catalog/toy/', base + '/catalog/home/']
    locs += [base + c.get_absolute_url() for c in Category.objects.filter(is_visible=True)]
    locs += [base + p.get_absolute_url() for p in Product.objects.all()]
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    body += [f'<url><loc>{loc}</loc></url>' for loc in locs]
    body.append('</urlset>')
    return HttpResponse('\n'.join(body), content_type='application/xml')


def robots_txt(request):
    lines = [
        'User-agent: *',
        'Disallow: /admin/',
        'Disallow: /cart/',
        'Disallow: /checkout/',
        'Sitemap: ' + request.build_absolute_uri('/sitemap.xml'),
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')
