from django.shortcuts import render, redirect
from .forms import TransactionForm
from .models import Transaction

def transaction_list_create(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('transaction-list')  # name of your URL route
    else:
        form = TransactionForm()

    transactions = Transaction.objects.all()
    return render(request, 'transactions/index.html', {'transactions': transactions, 'form': form})
