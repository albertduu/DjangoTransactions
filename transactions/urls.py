from django.urls import path
from . import views

urlpatterns = [
    path('payments/', views.payments, name='payments'),
    path('', views.transaction_list, name='transaction-list'),
    path('send-email/', views.send_email, name='send_email'),
    path('shipments/', views.shipments, name='shipments'),
    path('create-shipment/<int:transaction_id>/', views.create_shipment, name='create_shipment'),
    path('delete-shipment/<int:shipment_id>/', views.delete_shipment, name='delete_shipment')
]