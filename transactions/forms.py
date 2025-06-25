from django import forms
from django.utils import timezone
from .models import Transaction

class TransactionForm(forms.ModelForm):
    ts = forms.DateTimeField(
        initial=timezone.now,
        widget=forms.DateTimeInput(format='%Y-%m-%d %H:%M'),
        input_formats=['%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S']
    )
    class Meta:
        model = Transaction
        fields = '__all__'
