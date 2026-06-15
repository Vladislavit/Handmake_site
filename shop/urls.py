from django.urls import path

from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.home, name='home'),
    path('catalog/<slug:kind>/', views.world, name='world'),
    path('search/', views.search, name='search'),
    path('category/<slug:slug>/', views.category, name='category'),
    path('product/<slug:slug>/', views.product, name='product'),

    path('cart/', views.cart_detail, name='cart'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/update/<str:key>/', views.cart_update, name='cart_update'),
    path('cart/remove/<str:key>/', views.cart_remove, name='cart_remove'),

    path('checkout/', views.checkout, name='checkout'),
    path('checkout/done/<int:order_id>/', views.checkout_done, name='checkout_done'),

    path('np/cities/', views.np_cities, name='np_cities'),
    path('np/warehouses/', views.np_warehouses, name='np_warehouses'),
]
