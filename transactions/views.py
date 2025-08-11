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
        # When filtering by specific person, show detailed history
        transactions = Transaction.objects.filter(person_id=person_id)
        payments = Payment.objects.filter(transaction__person_id=person_id)
        
        transactions = transactions.annotate(
            total_transaction=ExpressionWrapper(
                F('quantity') * F('price'),
                output_field=DecimalField()
            )
        )

        # Create detailed history for the specific person
        tx_list = [
            {
                'date': t.ts,
                'type': 'Transaction',
                'amount': float(t.total_transaction)
            }
            for t in transactions
        ]
        
        pay_list = [
            {
                'date': p.date,
                'type': 'Payment', 
                'amount': float(p.amount)  # Keep positive for display
            }
            for p in payments.select_related('transaction')
        ]

        history = tx_list + pay_list
        history.sort(key=lambda x: x['date'], reverse=True)  # Most recent first

        # Calculate total remaining for this person
        total_transactions = transactions.aggregate(
            total=Sum(F('quantity') * F('price'), output_field=DecimalField())
        )['total'] or 0
        
        total_payments = payments.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        total_remaining = float(total_transactions) - float(total_payments)

        # Create summary entry for pagination compatibility
        summary_data = [{
            'person_id': person_id,
            'total_remaining': total_remaining
        }]
        
        paginator = Paginator(summary_data, 1)
        page_obj = paginator.get_page(1)

        return render(request, 'transactions/payments.html', {
            'payments': page_obj,
            'history': history
        })
    
    else:
        # Show summary of all people with outstanding balances
        from django.db.models import Q
        
        # Get all unique person_ids from transactions
        person_ids = Transaction.objects.values_list('person_id', flat=True).distinct()
        
        summary_data = []
        for pid in person_ids:
            if pid:  # Skip None/empty person_ids
                # Calculate total for this person
                person_transactions = Transaction.objects.filter(person_id=pid)
                person_payments = Payment.objects.filter(transaction__person_id=pid)
                
                total_transactions = person_transactions.aggregate(
                    total=Sum(F('quantity') * F('price'), output_field=DecimalField())
                )['total'] or 0
                
                total_payments = person_payments.aggregate(
                    total=Sum('amount')
                )['total'] or 0
                
                total_remaining = float(total_transactions) - float(total_payments)
                
                # Only show people with outstanding balances
                if total_remaining > 0:
                    summary_data.append({
                        'person_id': pid,
                        'total_remaining': total_remaining
                    })
        
        # Sort by total_remaining descending
        summary_data.sort(key=lambda x: x['total_remaining'], reverse=True)
        
        paginator = Paginator(summary_data, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return render(request, 'transactions/payments.html', {
            'payments': page_obj
        })


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