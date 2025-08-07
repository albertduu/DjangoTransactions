from django.shortcuts import render, get_object_or_404, redirect
from .models import Transaction, Shipment
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
        # Get all transactions for this person
        transactions = Transaction.objects.filter(person_id__icontains=person_id)

        # Calculate totals using DecimalField for consistency
        total_transaction = transactions.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('quantity') * F('price'),
                    output_field=DecimalField(max_digits=20, decimal_places=2)
                )
            )
        )['total'] or 0

        total_paid = transactions.aggregate(
            total=Sum('paid')
        )['total'] or 0

        # Calculate remaining amount using DecimalField wrapper
        total_remaining = total_transaction - total_paid

        # Sort all transactions chronologically (descending)
        combined = sorted(transactions, key=attrgetter('ts'), reverse=True)

        return render(request, 'transactions/person_transactions.html', {
            'transactions': combined,
            'person_id': person_id,
            'total_transaction': total_transaction,
            'total_paid': total_paid,
            'total_remaining': total_remaining,
        })

    else:
        # Summarized view of all users, ensuring DecimalField consistency
        payments = (
            Transaction.objects
            .values('person_id')
            .annotate(
                total_transaction=Sum(
                    ExpressionWrapper(
                        F('quantity') * F('price'),
                        output_field=DecimalField(max_digits=20, decimal_places=2)
                    )
                ),
                total_paid=Sum('paid')
            )
            .annotate(
                total_remaining=ExpressionWrapper(
                    F('total_transaction') - F('total_paid'),
                    output_field=DecimalField(max_digits=20, decimal_places=2)
                )
            )
            .order_by('-total_remaining')
        )

        paginator = Paginator(payments, 100)
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