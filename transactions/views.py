from django.shortcuts import render, redirect
from .models import Transaction
from .forms import TransactionForm
from django.db.models import F, Sum, ExpressionWrapper, FloatField

def transaction_list(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('transaction-list')  # avoid resubmission on refresh
    else:
        form = TransactionForm()
    
    transactions = Transaction.objects.all()
    return render(request, 'transactions/list.html', {
        'transactions': transactions,
        'form': form
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
