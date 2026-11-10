from django.db import models


class Payment(models.Model):
    """A record of an M-Pesa transaction initiated by this application."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    class Kind(models.TextChoices):
        C2B = "c2b", "Customer to business"
        B2C = "b2c", "Business to customer"

    kind = models.CharField(max_length=3, choices=Kind.choices, default=Kind.C2B)
    phone = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=20, db_index=True)
    description = models.CharField(max_length=256, blank=True)
    third_party_conversation_id = models.CharField(max_length=64, unique=True)
    conversation_id = models.CharField(max_length=64, blank=True, db_index=True)
    transaction_id = models.CharField(max_length=64, blank=True, db_index=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    response_code = models.CharField(max_length=16, blank=True)
    response_description = models.CharField(max_length=255, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return "%s %s TZS %s (%s)" % (self.reference, self.phone, self.amount, self.status)
