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
from django.db import connection
from decimal import Decimal

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
    person_id = request.GET.get('person_id', '').strip()
    entries = []
    all_balances = []

    if person_id:
        # --- Custom ledger query for single person ---
        with connection.cursor() as cursor:
            cursor.execute("SET @my_var:=0;")
            cursor.execute("""
                SELECT id, ts, notes, quantity, price, total, @my_var:=@my_var+a.total AS commutative_sum
                FROM (
                    (SELECT
                        t.id AS id, t.ts AS ts, p.product AS notes, t.quantity AS quantity, t.price AS price,
                        t.quantity*t.price AS total
                        FROM transactions t
                        LEFT JOIN transactions_product tp ON t.id=tp.t_id
                        LEFT JOIN products p ON tp.p_asin=p.asin
                        WHERE t.person_id=%s)
                    UNION ALL
                    (SELECT
                        p.id AS id, p.ts AS ts, p.notes AS notes, 0 AS quantity, 0 AS price,
                        -p.amount AS total
                        FROM payments p
                        WHERE p.t_person_id=%s)
                    ORDER BY ts, id
                ) a
                ORDER BY ts DESC, id DESC
                LIMIT 0, 100
            """, [person_id, person_id])

            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            for row in rows:
                entry = dict(zip(columns, row))
                # Ensure numeric fields are Decimal
                entry['quantity'] = Decimal(entry.get('quantity') or 0)
                entry['price'] = Decimal(entry.get('price') or 0)
                entry['total'] = Decimal(entry.get('total') or 0)
                entry['commutative_sum'] = Decimal(entry.get('commutative_sum') or 0)
                entries.append(entry)

    else:
        # --- Summary for all persons ---
        with connection.cursor() as cursor:
            # Get all unique person_ids from transactions and payments
            cursor.execute("""
                SELECT DISTINCT person_id FROM transactions
                UNION
                SELECT DISTINCT t_person_id FROM payments
            """)
            persons = [row[0] for row in cursor.fetchall()]

            # Compute balance per person
            for pid in persons:
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(t.quantity*t.price),0) - COALESCE(SUM(p.amount),0) AS total_remaining
                    FROM 
                        (SELECT quantity, price FROM transactions WHERE person_id=%s) t
                        LEFT JOIN
                        (SELECT amount FROM payments WHERE t_person_id=%s) p
                    ON 1=1
                """, [pid, pid])
                total_remaining = cursor.fetchone()[0] or 0
                all_balances.append({
                    'person_id': pid,
                    'total_remaining': Decimal(total_remaining)
                })

    return render(request, 'payments.html', {
        'entries': entries,
        'all_balances': all_balances,
        'person_id': person_id
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