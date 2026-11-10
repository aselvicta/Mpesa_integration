"""Backwards compatible ``client.stk`` interface from mpesa-tz 0.1.x."""


class STKPush:
    """Thin wrapper so ``client.stk.push(phone, amount, reference)`` keeps working."""

    def __init__(self, client):
        self._client = client

    def push(self, phone, amount, reference, description="Payment", conversation_id=None):
        return self._client.c2b_payment(
            phone=phone,
            amount=amount,
            reference=reference,
            description=description,
            conversation_id=conversation_id,
        )


# 0.1.x exported this name
STKpush = STKPush
