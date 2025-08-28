from django.shortcuts import render, get_object_or_404, redirect
from .models import Transaction, Shipment, Payment
from .forms import TransactionForm
from django.db.models import F, Sum, ExpressionWrapper, FloatField, IntegerField, DecimalField
from django.utils.dateparse import parse_date
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMessage
from django.urls import reverse
from operator import attrgetter
from itertools import chain

def transaction_list(request):
    form = TransactionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('transaction-list')

    # Filters
    transactions = Transaction.objects.all()
    person_id = request.GET.get('person_id')
    product = request.GET.get('product')
    in_stock = request.GET.get('in_stock')
    trackings = request.GET.get('trackings')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if person_id:
        transactions = transactions.filter(person_id__icontains=person_id)
    if product:
        transactions = transactions.filter(product__icontains=product)
    if in_stock:
        transactions = transactions.filter(quantity__gt=0)
    if trackings:
        transactions = transactions.filter(trackings__icontains=trackings)
    if start_date:
        transactions = transactions.filter(ts__date__gte=start_date)
    if end_date:
        transactions = transactions.filter(ts__date__lte=end_date)

    paginator = Paginator(transactions.order_by('-ts'), 200)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'transactions/list.html', {
        'transactions': page_obj,
        'form': form,
        'person_id': person_id,
        'product': product,
        'in_stock': in_stock,
        'trackings': trackings,
        'start_date': start_date,
        'end_date': end_date,
    })

def payments(request):
    person_id = request.GET.get('person_id')

    if person_id:
        transactions = Transaction.objects.filter(person_id__icontains=person_id).annotate(
            total=ExpressionWrapper(
                F('quantity') * F('price'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).values(
            'id', 'ts', 'product__product', 'quantity', 'price', 'total'
        )

        # Payments: total = -amount
        payments_qs = Payment.objects.filter(t_person_id__icontains=person_id).annotate(
            quantity=F('amount') * 0,   # always 0
            price=F('amount') * 0,      # always 0
            total=ExpressionWrapper(-F('amount'), output_field=DecimalField(max_digits=10, decimal_places=2))
        ).values(
            'id', 'ts', 'notes', 'quantity', 'price', 'total'
        )

        # Normalize keys
        tx_list = [
            {
                'id': t['id'],
                'ts': t['ts'],
                'notes': t['product__product'],
                'quantity': t['quantity'],
                'price': t['price'],
                'total': t['total'],
            }
            for t in transactions
        ]

        pay_list = [
            {
                'id': p['id'],
                'ts': p['ts'],
                'notes': p['notes'],
                'quantity': p['quantity'],
                'price': p['price'],
                'total': p['total'],
            }
            for p in payments_qs
        ]

        # Merge and sort by date/id
        combined = sorted(chain(tx_list, pay_list), key=lambda x: (x['ts'], x['id']))

        # Running balance
        running_sum = 0
        for row in combined:
            running_sum += row['total']
            row['commutative_sum'] = running_sum

        return render(request, 'payments.html', {'entries': combined})

    else:
        tx_totals = Transaction.objects.values('person_id').annotate(
            total=Sum(ExpressionWrapper(F('quantity')*F('price'), output_field=DecimalField(max_digits=10, decimal_places=2)))
        )

        # Payments per person
        pay_totals = Payment.objects.values('t_person_id').annotate(
            total=Sum('amount')
        )

        # Merge totals
        balance_dict = {}
        for t in tx_totals:
            balance_dict[t['person_id']] = t['total']
        for p in pay_totals:
            balance_dict[p['t_person_id']] = balance_dict.get(p['t_person_id'], 0) - p['total']

        all_balances = [{'person_id': k, 'total_remaining': v} for k, v in balance_dict.items()]

        return render(request, 'payments.html', {'all_balances': all_balances})

def send_email(request):
    if request.method == 'POST':
        recipient = request.POST['recipient']
        subject = request.POST['subject']
        message = request.POST['message']
        attachment = request.FILES.get('attachment')

        email = EmailMessage(subject, message, settings.EMAIL_HOST_USER, [recipient])
        if attachment:
            email.attach(attachment.name, attachment.read(), attachment.content_type)

        email.send()

        return redirect('transaction-list')
    
def shipments(request):
    shipments = Shipment.objects.select_related('transaction').order_by('-shipped_at')

    paginator = Paginator(shipments, 200)  # 200 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'transactions/shipments.html', {'shipments': page_obj})


# ✅ CREATE Shipment
def create_shipment(request, transaction_id):
    transaction = get_object_or_404(Transaction, pk=transaction_id)

    if request.method == 'POST':
        ship_qty = int(request.POST.get('ship_qty'))

        if 0 < ship_qty <= transaction.quantity:
            transaction.quantity -= ship_qty
            transaction.save()

            Shipment.objects.create(transaction=transaction, shipped_quantity=ship_qty)

        return redirect('shipments')

    return render(request, 'transactions/create_shipment.html', {'transaction': transaction})


# ✅ DELETE Shipment (restores Transaction qty)
def delete_shipment(request, shipment_id):
    shipment = get_object_or_404(Shipment, pk=shipment_id)
    transaction = shipment.transaction

    transaction.quantity += shipment.shipped_quantity
    transaction.save()

    shipment.delete()

    return redirect('shipments')