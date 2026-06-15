from django.contrib import admin
from django.utils.html import format_html

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


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'preview', 'alt', 'is_main', 'order')
    readonly_fields = ('preview',)

    def preview(self, obj):
        if obj and obj.image:
            return format_html('<img src="{}" style="height:60px;border-radius:8px">', obj.image.url)
        return '—'
    preview.short_description = 'Перегляд'


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
