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

    def __str__(self):
        return f"{self.person_id or 'N/A'} - {self.product}"
