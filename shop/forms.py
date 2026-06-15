from django import forms

from .models import Order


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'full_name', 'phone', 'email',
            'delivery', 'city', 'branch', 'address',
            'np_city_ref', 'np_warehouse_ref',
            'payment', 'comment',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Олена Коваль'}),
            'phone': forms.TextInput(attrs={'placeholder': '+380 __ ___ __ __', 'inputmode': 'tel'}),
            'email': forms.EmailInput(attrs={'placeholder': 'olena@example.com', 'inputmode': 'email'}),
            'city': forms.TextInput(attrs={'placeholder': 'Почніть вводити…', 'list': 'cities'}),
            'branch': forms.TextInput(attrs={'placeholder': '№ відділення'}),
            'address': forms.TextInput(attrs={'placeholder': 'Вулиця, будинок, квартира'}),
            'comment': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Напр.: подарункове пакування, побажання до кольору…',
            }),
        }

    def clean(self):
        cleaned = super().clean()
        delivery = cleaned.get('delivery')
        if delivery == 'pickup':
            return cleaned
        if not cleaned.get('city'):
            self.add_error('city', 'Вкажіть місто')
        if delivery == 'np-courier':
            if not cleaned.get('address'):
                self.add_error('address', 'Вкажіть адресу доставки')
        elif delivery == 'np-branch':
            if not cleaned.get('branch'):
                self.add_error('branch', 'Вкажіть відділення')
        return cleaned
