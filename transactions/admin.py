from django.contrib import admin
from .models import Transaction

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'ts', 'person_id', 'email', 'phone', 'location',
        'product', 'quantity', 'price', 'payment',
        'notes', 'asin', 'paid', 'trackings', 'shipped'
    )
    search_fields = ('person_id', 'email', 'product', 'asin')
    list_filter = ('location', 'payment', 'shipped')
