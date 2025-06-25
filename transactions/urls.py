from django.urls import path
from . import views

urlpatterns = [
    path('', views.transaction_list, name='transaction_list'),
    path('', views.transaction_list_create, name='transaction-list'),
]
