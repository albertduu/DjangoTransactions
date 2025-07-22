from django.shortcuts import render, redirect
from .models import Transaction
from .forms import TransactionForm
from django.db.models import Sum

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
    payments = (
        Transaction.objects
        .values('person_id')
        .annotate(total_remaining=Sum('payment'))
        .order_by('-total_remaining')
    )
    return render(request, 'transactions/payments.html', {'payments': payments})
