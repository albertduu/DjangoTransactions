from django.shortcuts import render, redirect
from .models import Transaction
from .forms import TransactionForm
from django.db.models import F, Sum, ExpressionWrapper, FloatField
from django.utils.dateparse import parse_date

def transaction_list(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('transaction-list')
    else:
        form = TransactionForm()

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

    return render(request, 'transactions/list.html', {
        'transactions': transactions,
        'form': form,
        'person_id': person_id,
        'product': product,
        'in_stock': in_stock,
        'trackings': trackings,
        'start_date': start_date,
        'end_date': end_date,
    })

def payments(request):
    query = request.GET.get('person_id')  # get search input
    payments = (
        Transaction.objects
        .values('person_id')
        .annotate(
            total_payment=Sum(
                ExpressionWrapper(
                    F('quantity') * F('price'),
                    output_field=FloatField()
                )
            )
        )
        .order_by('-total_payment')
    )

    if query:
        payments = payments.filter(person_id__icontains=query)

    return render(request, 'transactions/payments.html', {'payments': payments, 'query': query})
