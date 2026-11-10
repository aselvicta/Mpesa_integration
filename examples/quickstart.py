"""Plain Python example. Configure MPESA_* variables (see .env.example) first."""

from mpesa_tz import MpesaClient, MpesaError, generate_reference

client = MpesaClient.from_env(session_activation_delay=5)  # sandbox needs a short warm-up

try:
    result = client.stk_push(
        phone="0754123456",
        amount=1000,
        reference=generate_reference("ORDER"),
        description="Order payment",
    )
    print("Paid!", result.transaction_id, result.description)
except MpesaError as exc:
    print("Payment failed:", exc)
