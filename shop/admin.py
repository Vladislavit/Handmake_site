from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .cloudinary_service import CloudinaryUploadError, upload_product_image
from .models import (
    Category, NPCity, NPWarehouse, Order, OrderItem, Product, ProductImage,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'kind', 'order', 'is_visible')
    list_filter = ('kind', 'is_visible')
    list_editable = ('order', 'is_visible')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


def _img_tag(url, height=60):
    """Клікабельне прев'ю (відкриває повне фото в новій вкладці)."""
    return format_html(
        '<a href="{0}" target="_blank" rel="noopener">'
        '<img src="{0}" style="height:{1}px;border-radius:10px;'
        'border:1px solid #e2d7c5;background:#fff"></a>',
        url, height,
    )


class ProductImageForm(forms.ModelForm):
    """Дозволяє завантажити файл — він піде в Cloudinary, а в БД ляже secure_url."""
    upload = forms.ImageField(
        required=False, label='Завантажити / замінити фото',
        help_text='Залиште порожнім — поточне фото лишиться без змін.',
    )
    process = forms.BooleanField(
        required=False, initial=True, label='Обробити фото',
        help_text='Видалити фон, додати тінь і біле тло, обрізати в квадрат. '
                  'Зніміть галочку, щоб завантажити фото як є (лише веб-оптимізація).',
    )

    class Meta:
        model = ProductImage
        fields = ('upload', 'process', 'image_url', 'alt', 'is_main', 'order')

    def clean(self):
        cleaned = super().clean()
        upload = cleaned.get('upload')
        if upload:
            try:
                url = upload_product_image(upload, process=cleaned.get('process', False))
            except CloudinaryUploadError as exc:
                self.add_error('upload', str(exc))
            else:
                cleaned['image_url'] = url
                self.instance.image_url = url
        elif self.has_changed() and not cleaned.get('image_url'):
            self.add_error('upload', 'Додайте фото (файл) або вкажіть URL.')
        return cleaned


class ProductImageInline(admin.StackedInline):
    model = ProductImage
    form = ProductImageForm
    extra = 1
    fields = ('preview', 'upload', 'process', 'image_url', 'alt', 'is_main', 'order')
    readonly_fields = ('preview',)

    def preview(self, obj):
        if obj and obj.image_url:
            return _img_tag(obj.image_url, height=160)
        return format_html('<span style="color:#7A6B60">Фото ще немає — завантажте файл нижче.</span>')
    preview.short_description = 'Поточне фото'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'badge', 'is_available', 'is_coming_soon')
    list_filter = ('category', 'category__kind', 'is_available', 'is_coming_soon', 'badge')
    list_editable = ('price', 'is_available')
    search_fields = ('name', 'meta', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]
    fieldsets = (
        (None, {
            'fields': ('category', 'name', 'slug', 'meta', 'description'),
        }),
        ('Ціна', {
            'fields': ('price', 'old_price'),
        }),
        ('Опції (текстом)', {
            'fields': ('sizes', 'colors', 'badge'),
            'description': 'Розмір/колір — необов\'язкові. Кольори у форматі «назва:#HEX».',
        }),
        ('Вигляд без фото (SVG-балванка)', {
            'classes': ('collapse',),
            'fields': ('placeholder', 'color1', 'color2'),
            'description': 'Показується, доки не завантажено фото товару.',
        }),
        ('Стан і рейтинг', {
            'fields': ('is_available', 'is_coming_soon', 'rating', 'reviews_count'),
        }),
    )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('product', 'name', 'options', 'price', 'qty', 'cost')
    readonly_fields = ('cost',)

    def cost(self, obj):
        return f'{obj.cost} ₴'
    cost.short_description = 'Сума'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone', 'total', 'delivery', 'payment', 'status', 'created')
    list_filter = ('status', 'delivery', 'payment', 'created')
    list_editable = ('status',)
    search_fields = ('full_name', 'phone', 'email')
    readonly_fields = ('shipping', 'total', 'created')
    inlines = [OrderItemInline]
    fieldsets = (
        ('Клієнт', {'fields': ('full_name', 'phone', 'email')}),
        ('Доставка', {'fields': ('delivery', 'city', 'branch', 'address',
                                 'np_city_ref', 'np_warehouse_ref')}),
        ('Оплата та коментар', {'fields': ('payment', 'comment')}),
        ('Підсумки', {'fields': ('shipping', 'total', 'status', 'created')}),
    )


class ProductImageAdminForm(ProductImageForm):
    """Та сама логіка завантаження, але з вибором товару (для окремого розділу)."""
    class Meta(ProductImageForm.Meta):
        fields = ('product', 'upload', 'image_url', 'alt', 'is_main', 'order')


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    form = ProductImageAdminForm
    list_display = ('thumb', 'product', 'alt', 'is_main', 'order')
    list_display_links = ('thumb', 'product')
    list_filter = ('is_main', 'product__category')
    search_fields = ('product__name', 'alt')
    list_select_related = ('product',)
    readonly_fields = ('preview',)
    fields = ('product', 'preview', 'upload', 'process', 'image_url', 'alt', 'is_main', 'order')

    def thumb(self, obj):
        if obj.image_url:
            return _img_tag(obj.image_url, height=54)
        return '—'
    thumb.short_description = 'Фото'

    def preview(self, obj):
        if obj and obj.image_url:
            return _img_tag(obj.image_url, height=200)
        return format_html('<span style="color:#7A6B60">Фото ще немає — завантажте файл нижче.</span>')
    preview.short_description = 'Поточне фото'


@admin.register(NPCity)
class NPCityAdmin(admin.ModelAdmin):
    list_display = ('name', 'area', 'ref')
    search_fields = ('name', 'area', 'ref')


@admin.register(NPWarehouse)
class NPWarehouseAdmin(admin.ModelAdmin):
    list_display = ('description', 'city', 'number', 'is_poshtomat')
    list_filter = ('is_poshtomat', 'category')
    search_fields = ('description', 'short_address', 'number', 'city__name')
    list_select_related = ('city',)
    raw_id_fields = ('city',)


admin.site.site_header = 'Клубок — адміністрування'
admin.site.site_title = 'Клубок'
admin.site.index_title = 'Магазин'
