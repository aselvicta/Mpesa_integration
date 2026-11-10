# mpesa-tz

A lightweight, developer-friendly Python package for **M-Pesa Tanzania** (Vodacom M-Pesa OpenAPI).

Works with Django, Flask, FastAPI or plain Python.

## Features

- **STK push / C2B** – prompt a customer to pay from their phone
- **B2C** (pay a customer), **B2B** (pay another business)
- **Transaction status query** and **reversal**
- Automatic OAuth-style session handling: the API key is RSA-encrypted, a session key is fetched, cached and refreshed (with one automatic retry if M-Pesa rejects it)
- Input validation (Tanzanian phone numbers, amounts, references) **before** anything is sent
- Typed exceptions plus human-readable `INS-*` response codes
- Sandbox and production support, config from environment / `.env`
- Async callback parsing + acknowledgement helpers
- Optional Django app (Payment model, admin, callback view)
- CLI for quick checks: `mpesa-tz session`, `mpesa-tz stk-push ...`

## Installation

```bash
pip install mpesa-tz              # core
pip install "mpesa-tz[dotenv]"    # + .env file support
pip install "mpesa-tz[django]"    # + Django integration
```

Requires Python 3.8+.

## Credentials

Create an application on the [M-Pesa OpenAPI portal](https://openapiportal.m-pesa.com) (market: Vodacom Tanzania) and collect:

| Variable | What it is |
|---|---|
| `MPESA_API_KEY` | Your application's API key |
| `MPESA_PUBLIC_KEY` | Public key shown on the portal (sandbox and production keys differ) |
| `MPESA_SERVICE_PROVIDER_CODE` | Your business shortcode (sandbox: `000000`) |
| `MPESA_ENVIRONMENT` | `sandbox` (default) or `production` |
| `MPESA_ORIGIN` | Origin header, default `*` |

Copy `.env.example` to `.env` and fill it in.

## Quick start

```python
from mpesa_tz import MpesaClient, MpesaAPIError, MpesaError

client = MpesaClient(
    api_key="YOUR_API_KEY",
    public_key="MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEA...",
    service_provider_code="000000",
    environment="sandbox",
)
# or: client = MpesaClient.from_env()

try:
    result = client.stk_push(
        phone="0754123456",       # 0754..., 754..., +255 754 ..., 255754... all work
        amount=1000,              # TZS
        reference="ORDER1",       # 1-20 alphanumeric characters
        description="Order #1",
    )
    print(result.transaction_id, result.conversation_id, result.description)
except MpesaAPIError as exc:      # M-Pesa answered with an error
    print(exc.code, exc.description)   # e.g. INS-5 "Transaction cancelled by customer"
except MpesaError as exc:         # validation, config or network problem
    print(exc)
```

> The C2B single-stage call **blocks until the customer enters their PIN** (or the request times out). The default timeout is 60 seconds. In web apps, run it in a worker or thread.

### Other operations

```python
client.b2c_payment("0754123456", 5000, "PAYOUT1", "Refund")
client.b2b_payment("888888", 100000, "INV1", "Supplier invoice")
client.query_transaction_status("TX123ABC")      # transaction id, conversation id or reference
client.reversal("TX123ABC", 1000)
```

Each call returns an `MpesaResponse` with `.is_success`, `.code`, `.description`,
`.transaction_id`, `.conversation_id`, `.third_party_conversation_id`, `.raw` and `.to_dict()`.

### Errors

| Exception | When |
|---|---|
| `MpesaValidationError` | Bad phone / amount / reference (nothing is sent) |
| `MpesaConfigError` | Missing API key, public key, shortcode, bad environment |
| `MpesaConnectionError` | Timeout, DNS, TLS problems |
| `MpesaAuthError` | Invalid API key / not authorised (`INS-2`, `INS-26`) |
| `MpesaAPIError` | Any other `INS-*` error – see `exc.code`, `exc.description`, `exc.response` |

All of them inherit from `MpesaError`. Pass `raise_on_error=False` to get an unsuccessful
`MpesaResponse` instead of an exception for API errors.

### Useful options

```python
MpesaClient(
    ...,
    timeout=60,                    # seconds
    session_ttl=3000,              # reuse a session key this long
    session_activation_delay=30,   # sandbox: new session keys take a moment to activate
    strict_phone=None,             # default: strict TZ numbers in production, relaxed in sandbox
    http_session=requests.Session(),
)
```

## Async callbacks

If your account delivers results to a callback URL:

```python
from mpesa_tz import parse_callback, callback_ack

result = parse_callback(request_body)      # dict, str or bytes
if result.is_success:
    mark_order_paid(result.third_party_conversation_id, result.transaction_id)
return callback_ack(result)                # JSON body M-Pesa expects back
```

## Django

```python
# settings.py
INSTALLED_APPS += ["mpesa_tz.contrib.django"]
MPESA_TZ = {                      # optional; falls back to MPESA_* env vars
    "SERVICE_PROVIDER_CODE": "000000",
    "ENVIRONMENT": "sandbox",
}

# urls.py
path("mpesa/", include("mpesa_tz.contrib.django.urls")),   # POST /mpesa/callback/
```

```bash
python manage.py migrate
```

```python
from mpesa_tz.contrib.django.services import initiate_stk_push

payment = initiate_stk_push("0754123456", 1000, "ORDER1")   # stores a Payment row
payment.status   # "success" / "failed" ("pending" if the network failed - query it later)
```

Payments are visible in the Django admin.

## Flask / FastAPI

See [`examples/flask_app.py`](examples/flask_app.py) and [`examples/fastapi_app.py`](examples/fastapi_app.py).

## CLI

```bash
mpesa-tz session                                                   # check credentials
mpesa-tz stk-push --phone 0754123456 --amount 1000 --reference ORDER1
mpesa-tz b2c --phone 0754123456 --amount 500 --reference PAY1
mpesa-tz query --reference TX123ABC
mpesa-tz reverse --transaction-id TX123ABC --amount 1000
```

(`python -m mpesa_tz ...` works too.) Output is JSON; the exit code is non-zero on failure.

## Upgrading from 0.1.0

`client.stk.push(phone=..., amount=..., reference=...)` still works, but the client now
needs the real credentials:

```python
# 0.1.0
MpesaClient(api_key=..., base_url=...)
# 0.2.0
MpesaClient(api_key=..., public_key=..., service_provider_code=..., environment="sandbox")
```

## Testing

See [TESTING.md](TESTING.md).

## License

MIT
