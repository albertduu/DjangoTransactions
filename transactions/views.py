from django.shortcuts import render, redirect
from .models import Transaction
from .forms import TransactionForm

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
