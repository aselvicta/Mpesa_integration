from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "kind", "phone", "amount", "status", "response_code", "transaction_id", "created_at")
    list_filter = ("status", "kind", "created_at")
    search_fields = ("reference", "phone", "transaction_id", "conversation_id", "third_party_conversation_id")
    readonly_fields = ("raw_response", "created_at", "updated_at")
