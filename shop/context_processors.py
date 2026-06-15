from .cart import Cart
from .models import Category


def cart(request):
    return {'cart': Cart(request)}


def nav_categories(request):
    """Категорії для навігації/підвалу, згруповані за світом."""
    cats = Category.objects.filter(is_visible=True)
    return {
        'nav_toy_categories': [c for c in cats if c.kind == Category.KIND_TOY],
        'nav_home_categories': [c for c in cats if c.kind == Category.KIND_HOME],
    }
