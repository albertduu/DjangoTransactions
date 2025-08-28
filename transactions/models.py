from django.db import models

class Transaction(models.Model):
    ts = models.DateTimeField()
    person_id = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    location = models.CharField(max_length=10)
    product = models.CharField(max_length=200)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    payment = models.CharField(max_length=50)

    # Additional fields
    notes = models.TextField(null=True, blank=True)
    asin = models.CharField(max_length=20, null=True, blank=True)
    paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    trackings = models.TextField(null=True, blank=True)
    shipped = models.BooleanField(default=False)

    class Meta:
        db_table = 'transactions'

    def __str__(self):
        return f"{self.person_id or 'N/A'} - {self.product}"
    
class Payment(models.Model):
    id = models.AutoField(primary_key=True)
    ts = models.DateTimeField()  # corresponds to 'ts' column
    t_person_id = models.CharField(max_length=255)  # person ID string
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'payments'  # explicitly map to your existing table

    def __str__(self):
        return f"{self.t_person_id} - {self.amount}"
    
class Shipment(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)
    shipped_quantity = models.IntegerField()
    shipped_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Shipment of {self.shipped_quantity} for {self.transaction}"
