from django.urls import path
from . import views

urlpatterns = [
    path('payments/', views.payments, name='payments'),
    path('', views.transaction_list, name='transaction-list'),
    path('send-email/', views.send_email, name='send_email'),
]
