from django.db import models
from django.urls import reverse
from django.utils import timezone

from .utils import unique_slugify


class Category(models.Model):
    """Розділ каталогу. `kind` визначає «світ» і акцентний колір теми."""

    KIND_TOY = 'toy'
    KIND_HOME = 'home'
    KIND_CHOICES = [
        (KIND_TOY, 'Іграшки'),
        (KIND_HOME, 'Для дому'),
    ]

    name = models.CharField('Назва', max_length=120)
    slug = models.SlugField('Slug', max_length=140, unique=True, blank=True,
                            help_text='Залиште порожнім — згенерується з назви (латиницею).')
    kind = models.CharField('Світ', max_length=10, choices=KIND_CHOICES, default=KIND_TOY)
    eyebrow = models.CharField('Надзаголовок', max_length=80, blank=True)
    description = models.TextField('Опис', blank=True)
    order = models.PositiveIntegerField('Порядок', default=0)
    is_visible = models.BooleanField('Показувати', default=True)

    class Meta:
        verbose_name = 'Категорія'
        verbose_name_plural = 'Категорії'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('shop:category', args=[self.slug])

    @property
    def is_home(self):
        return self.kind == self.KIND_HOME


class Product(models.Model):
    """Товар. Опції (розмір/колір) — текстові, як домовлено."""

    BADGE_CHOICES = [
        ('', '—'),
        ('Хіт', 'Хіт'),
        ('Новинка', 'Новинка'),
        ('Великий', 'Великий'),
    ]
    # SVG-«балванка», яку показуємо доти, доки не завантажено фото
    PLACEHOLDER_BUNNY = 'bunny'
    PLACEHOLDER_HANGING = 'hanging'
    PLACEHOLDER_WOVEN = 'woven'
    PLACEHOLDER_CHAIN = 'chain'
    PLACEHOLDER_CHOICES = [
        (PLACEHOLDER_BUNNY, 'Зайчик'),
        (PLACEHOLDER_HANGING, 'Кашпо підвісне'),
        (PLACEHOLDER_WOVEN, 'Кашпо плетене'),
        (PLACEHOLDER_CHAIN, 'Кашпо на ланцюжку'),
    ]

    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='products', verbose_name='Категорія'
    )
    name = models.CharField('Назва', max_length=140)
    slug = models.SlugField('Slug', max_length=160, unique=True, blank=True,
                            help_text='Залиште порожнім — згенерується з назви (латиницею).')
    meta = models.CharField('Короткий опис', max_length=120, blank=True,
                            help_text='Напр.: «26 см · вершковий»')
    description = models.TextField('Опис', blank=True)

    price = models.DecimalField('Ціна, ₴', max_digits=8, decimal_places=0, default=0)
    old_price = models.DecimalField('Стара ціна, ₴', max_digits=8, decimal_places=0,
                                    null=True, blank=True, help_text='Для перекресленої ціни')

    badge = models.CharField('Бейдж', max_length=12, choices=BADGE_CHOICES, blank=True, default='')
    sizes = models.CharField('Розміри', max_length=200, blank=True,
                             help_text='Через кому: 18 см, 22 см, 26 см')
    colors = models.CharField('Кольори', max_length=300, blank=True,
                              help_text='Через кому, формат «назва:#HEX»: вершковий:#EFE7D7, сірий:#B7BCC0')

    placeholder = models.CharField('SVG-балванка', max_length=12, choices=PLACEHOLDER_CHOICES,
                                   default=PLACEHOLDER_BUNNY)
    color1 = models.CharField('Колір SVG (світлий)', max_length=7, default='#C5806C')
    color2 = models.CharField('Колір SVG (темний)', max_length=7, default='#A4604D')

    rating = models.DecimalField('Рейтинг', max_digits=2, decimal_places=1, default=0)
    reviews_count = models.PositiveIntegerField('Відгуків', default=0)

    is_available = models.BooleanField('В наявності', default=True)
    is_coming_soon = models.BooleanField('Очікується', default=False)
    created = models.DateTimeField('Створено', default=timezone.now, editable=False)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товари'
        ordering = ['-created']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('shop:product', args=[self.slug])

    @property
    def has_discount(self):
        return self.old_price and self.old_price > self.price

    @property
    def main_image_url(self):
        img = self.images.filter(is_main=True).first() or self.images.first()
        return img.image_url if img else None

    def size_list(self):
        return [s.strip() for s in self.sizes.split(',') if s.strip()]

    def color_list(self):
        """Повертає [{'name': ..., 'hex': ...}] із поля colors."""
        out = []
        for chunk in self.colors.split(','):
            chunk = chunk.strip()
            if not chunk:
                continue
            name, _, hex_ = chunk.partition(':')
            out.append({'name': name.strip(), 'hex': (hex_.strip() or '#E2D7C5')})
        return out


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images',
                                verbose_name='Товар')
    # secure_url від Cloudinary (фото обробляється і зберігається в хмарі, не локально)
    image_url = models.URLField('URL фото (Cloudinary)', max_length=500, blank=True)
    alt = models.CharField('Опис (alt)', max_length=140, blank=True)
    is_main = models.BooleanField('Головне', default=False)
    order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Фото товару'
        verbose_name_plural = 'Фото товарів'
        ordering = ['-is_main', 'order', 'id']

    def __str__(self):
        return f'Фото #{self.pk} — {self.product.name}'


class Order(models.Model):
    DELIVERY_CHOICES = [
        ('np-branch', 'Нова Пошта — відділення'),
        ('np-courier', 'Нова Пошта — кур\'єр'),
        ('pickup', 'Самовивіз'),
    ]
    PAYMENT_CHOICES = [
        ('online', 'Картка онлайн'),
        ('cod', 'Накладений платіж'),
    ]
    STATUS_CHOICES = [
        ('new', 'Новий'),
        ('processing', 'В обробці'),
        ('done', 'Виконано'),
        ('cancelled', 'Скасовано'),
    ]

    full_name = models.CharField('Ім\'я та прізвище', max_length=140)
    phone = models.CharField('Телефон', max_length=40)
    email = models.EmailField('Email', blank=True)

    delivery = models.CharField('Доставка', max_length=20, choices=DELIVERY_CHOICES,
                                default='np-branch')
    city = models.CharField('Місто', max_length=120, blank=True)
    branch = models.CharField('Відділення / поштомат', max_length=255, blank=True)
    address = models.CharField('Адреса', max_length=255, blank=True)
    np_city_ref = models.CharField('Ref міста НП', max_length=64, blank=True)
    np_warehouse_ref = models.CharField('Ref відділення НП', max_length=64, blank=True)

    payment = models.CharField('Оплата', max_length=20, choices=PAYMENT_CHOICES, default='online')
    comment = models.TextField('Коментар', blank=True)

    shipping = models.DecimalField('Доставка, ₴', max_digits=8, decimal_places=0, default=0)
    total = models.DecimalField('Разом, ₴', max_digits=10, decimal_places=0, default=0)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='new')
    created = models.DateTimeField('Створено', default=timezone.now, editable=False)

    class Meta:
        verbose_name = 'Замовлення'
        verbose_name_plural = 'Замовлення'
        ordering = ['-created']

    def __str__(self):
        return f'Замовлення №{self.pk}'

    def delivery_label(self):
        """Зрозумілий підпис доставки: відділення це чи поштомат."""
        if self.delivery == 'pickup':
            return 'Самовивіз'
        if self.delivery == 'np-courier':
            return 'Нова Пошта — кур\'єр'
        if 'поштомат' in (self.branch or '').lower():
            return 'Нова Пошта — поштомат'
        return 'Нова Пошта — відділення'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items',
                              verbose_name='Замовлення')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True,
                                verbose_name='Товар')
    name = models.CharField('Назва', max_length=160)
    options = models.CharField('Опції', max_length=200, blank=True)
    price = models.DecimalField('Ціна, ₴', max_digits=8, decimal_places=0, default=0)
    qty = models.PositiveIntegerField('Кількість', default=1)

    class Meta:
        verbose_name = 'Позиція замовлення'
        verbose_name_plural = 'Позиції замовлення'

    def __str__(self):
        return f'{self.name} × {self.qty}'

    @property
    def cost(self):
        return self.price * self.qty


class NPCity(models.Model):
    """Місто/населений пункт Нової Пошти (наповнюється sync_novaposhta)."""
    ref = models.CharField('Ref', max_length=64, unique=True)
    name = models.CharField('Назва', max_length=160, db_index=True)
    area = models.CharField('Область', max_length=160, blank=True)

    class Meta:
        verbose_name = 'НП: місто'
        verbose_name_plural = 'НП: міста'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.area})' if self.area else self.name


class NPWarehouse(models.Model):
    """Відділення або поштомат Нової Пошти."""
    ref = models.CharField('Ref', max_length=64, unique=True)
    city = models.ForeignKey(NPCity, on_delete=models.CASCADE, related_name='warehouses',
                             verbose_name='Місто')
    number = models.CharField('Номер', max_length=20, blank=True)
    description = models.CharField('Назва/адреса', max_length=255)
    short_address = models.CharField('Коротка адреса', max_length=255, blank=True)
    category = models.CharField('Категорія НП', max_length=40, blank=True)
    is_poshtomat = models.BooleanField('Поштомат', default=False)
    lat = models.FloatField('Широта', null=True, blank=True)
    lng = models.FloatField('Довгота', null=True, blank=True)

    class Meta:
        verbose_name = 'НП: відділення'
        verbose_name_plural = 'НП: відділення'
        ordering = ['city__name', 'number']
        indexes = [models.Index(fields=['city', 'is_poshtomat'])]

    def __str__(self):
        return self.description
