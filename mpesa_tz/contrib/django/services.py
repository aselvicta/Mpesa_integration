"""High level helpers that call M-Pesa and persist the result."""

from django.conf import settings

from ...client import MpesaClient
from ...exceptions import MpesaAPIError
from ...utils import format_amount, generate_conversation_id, normalize_phone
from .models import Payment


def get_client():
    """Build an MpesaClient from ``settings.MPESA_TZ`` / MPESA_* env vars."""
    conf = getattr(settings, "MPESA_TZ", {}) or {}
    overrides = {
        key: conf[name]
        for name, key in (
            ("API_KEY", "api_key"),
            ("PUBLIC_KEY", "public_key"),
            ("SERVICE_PROVIDER_CODE", "service_provider_code"),
            ("ENVIRONMENT", "environment"),
            ("BASE_URL", "base_url"),
            ("ORIGIN", "origin"),
            ("TIMEOUT", "timeout"),
        )
        if conf.get(name) is not None
    }
    return MpesaClient.from_env(**overrides)


def _apply(payment, response_code, description, raw, transaction_id=None, conversation_id=None):
    payment.response_code = response_code or ""
    payment.response_description = (description or "")[:255]
    payment.raw_response = raw or {}
    payment.transaction_id = transaction_id or payment.transaction_id
    payment.conversation_id = conversation_id or payment.conversation_id


def _run(kind, method, phone, amount, reference, description, client):
    client = client or get_client()
    payment = Payment.objects.create(
        kind=kind,
        phone=normalize_phone(phone),
        amount=format_amount(amount),
        reference=reference,
        description=description,
        third_party_conversation_id=generate_conversation_id(),
    )
    try:
        result = getattr(client, method)(
            phone, amount, reference, description, conversation_id=payment.third_party_conversation_id
        )
    except MpesaAPIError as exc:
        _apply(payment, exc.code, exc.description, exc.response,
               transaction_id=exc.response.get("output_TransactionID"),
               conversation_id=exc.response.get("output_ConversationID"))
        payment.status = Payment.Status.FAILED
        payment.save()
        raise
    _apply(payment, result.code, result.description, result.raw, result.transaction_id, result.conversation_id)
    payment.status = Payment.Status.SUCCESS if result.is_success else Payment.Status.FAILED
    payment.save()
    return payment


def initiate_stk_push(phone, amount, reference, description="Payment", client=None):
    """Prompt the customer to pay and store a :class:`Payment` record."""
    return _run(Payment.Kind.C2B, "c2b_payment", phone, amount, reference, description, client)


def send_b2c_payment(phone, amount, reference, description="Payment", client=None):
    """Pay a customer and store a :class:`Payment` record."""
    return _run(Payment.Kind.B2C, "b2c_payment", phone, amount, reference, description, client)


def apply_callback(result):
    """Update the matching Payment from a parsed :class:`CallbackResult`."""
    payment = None
    if result.third_party_conversation_id:
        payment = Payment.objects.filter(third_party_conversation_id=result.third_party_conversation_id).first()
    if payment is None and result.conversation_id:
        payment = Payment.objects.filter(conversation_id=result.conversation_id).first()
    if payment is None:
        return None
    _apply(payment, result.result_code, result.result_description, result.raw,
           result.transaction_id, result.conversation_id)
    payment.status = Payment.Status.SUCCESS if result.is_success else Payment.Status.FAILED
    payment.save()
    return payment
