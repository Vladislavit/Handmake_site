import re

from django import forms

from .models import Order


class CheckoutForm(forms.ModelForm):
    # Honeypot: приховане поле. Люди його не бачать; боти заповнюють усі поля.
    website = forms.CharField(
        required=False, label='', help_text='',
        widget=forms.TextInput(attrs={'autocomplete': 'off', 'tabindex': '-1'}),
    )

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
            'phone': forms.TextInput(attrs={'placeholder': '+380 67 123 45 67', 'inputmode': 'tel', 'maxlength': '20'}),
            'email': forms.EmailInput(attrs={'placeholder': 'olena@example.com', 'inputmode': 'email'}),
            'city': forms.TextInput(attrs={'placeholder': 'Почніть вводити…', 'list': 'cities'}),
            'branch': forms.TextInput(attrs={'placeholder': '№ відділення'}),
            'address': forms.TextInput(attrs={'placeholder': 'Вулиця, будинок, квартира'}),
            'comment': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Напр.: подарункове пакування, побажання до кольору…',
            }),
        }

    def clean_phone(self):
        """Перевірка й нормалізація українського номера до +380XXXXXXXXX."""
        raw = self.cleaned_data.get('phone', '')
        digits = re.sub(r'\D', '', raw)          # лишаємо тільки цифри

        if digits.startswith('380') and len(digits) == 12:
            normalized = '+' + digits
        elif digits.startswith('0') and len(digits) == 10:
            normalized = '+38' + digits          # 0XXXXXXXXX -> +380XXXXXXXXX
        elif len(digits) == 9:
            normalized = '+380' + digits          # XXXXXXXXX -> +380XXXXXXXXX
        else:
            raise forms.ValidationError(
                'Введіть коректний номер телефону, напр. +380 67 123 45 67'
            )
        return normalized

    def clean(self):
        cleaned = super().clean()
        # Honeypot спрацював -> це бот
        if cleaned.get('website'):
            raise forms.ValidationError('Не вдалося оформити замовлення.')
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
