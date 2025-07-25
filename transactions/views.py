from django.shortcuts import render, redirect
from .models import Transaction
from .forms import TransactionForm
from django.db.models import F, Sum, ExpressionWrapper, FloatField
from django.utils.dateparse import parse_date
from django.core.paginator import Paginator

def transaction_list(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('transaction-list')
    else:
        form = TransactionForm()

    # filters
    person_id = request.GET.get('person_id')
    product = request.GET.get('product')
    in_stock = request.GET.get('in_stock')
    trackings = request.GET.get('trackings')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    transactions = Transaction.objects.all()

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

    # ✅ Paginate main list
    paginator = Paginator(transactions, 200)
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
        # ✅ If filtering a specific person, show their transactions
        transactions = Transaction.objects.filter(person_id__icontains=person_id).order_by('-ts')

        # ✅ Pagination — 200 per page
        paginator = Paginator(transactions, 200)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return render(request, 'transactions/person_transactions.html', {
            'transactions': page_obj,
            'person_id': person_id
        })

    # ✅ Otherwise, show summed payments
    payments = (
        Transaction.objects
        .values('person_id')
        .annotate(total_remaining=Sum(F('quantity') * F('price')))
        .order_by('-total_remaining')
    )
    return render(request, 'transactions/payments.html', {'payments': payments})