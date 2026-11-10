# Quick start

Get from zero to your first M-Pesa Tanzania payment request in about 10 minutes.

> Overview: [README.md](README.md) · API reference: [Reference](#reference) below · Validating the package: [TESTING.md](TESTING.md)

---

## 1. Install

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install "mpesa-tz[dotenv]"     # [dotenv] lets the client read a .env file
```

If you use Django, install `"mpesa-tz[django,dotenv]"` instead.

---

## 2. Get sandbox credentials

1. Sign up at <https://openapiportal.m-pesa.com>.
2. Create an application and choose **Vodacom Tanzania** as the market and **Sandbox** as the environment.
3. Copy these values:
   - **API key**
   - **Public key** (the sandbox one; production uses a different key)
   - **Service provider code**, which is `000000` in the sandbox
   - **Test phone number (MSISDN)** listed in the portal docs, e.g. `000000000001`

---

## 3. Configure

Create a `.env` file in your project folder:

```dotenv
MPESA_API_KEY=paste-your-api-key
MPESA_PUBLIC_KEY=paste-the-whole-public-key
MPESA_SERVICE_PROVIDER_CODE=000000
MPESA_ENVIRONMENT=sandbox
```

Add `.env` to your `.gitignore`. **Never commit credentials.**

---

## 4. Check your credentials

```bash
mpesa-tz session
```

Expected output:

```json
{
  "ok": true,
  "message": "Session key obtained",
  "environment": "sandbox"
}
```

If you get `"ok": false`, see [Common problems](#common-problems) below.

The sandbox can take up to about 30 seconds to activate a new session key, so wait a moment before the next step.

---

## 5. Send your first payment request (STK push)

From the terminal:

```bash
mpesa-tz stk-push --phone 000000000001 --amount 100 --reference TEST001
```

Or in Python, in a file `pay.py`:

```python
from mpesa_tz import MpesaClient, MpesaAPIError, MpesaError, generate_reference

# Reads MPESA_* values from .env.
# session_activation_delay gives a new sandbox session key time to activate.
client = MpesaClient.from_env(session_activation_delay=30)

try:
    result = client.stk_push(
        phone="000000000001",                 # in production: "0754123456", "+255 754 123 456", ...
        amount=100,                           # TZS
        reference=generate_reference("ORDER"),  # unique, 1-20 letters/digits
        description="Test payment",
    )
    print("Success!")
    print("Transaction ID:", result.transaction_id)
    print("Conversation ID:", result.conversation_id)
except MpesaAPIError as exc:
    # M-Pesa answered with an error, e.g. INS-5 = customer cancelled
    print("M-Pesa error:", exc.code, exc.description)
except MpesaError as exc:
    # Bad input, missing config or network problem
    print("Error:", exc)
```

```bash
python pay.py
```

In production, the customer's phone shows a PIN prompt. The `stk_push` call **waits**
until they confirm or cancel, or until the request times out (60 seconds by default).

---

## 6. Check or undo a transaction

```python
status = client.query_transaction_status(result.transaction_id)
print(status.raw)

client.reversal(result.transaction_id, 100)   # refund the payment
```

Other operations: `client.b2c_payment(...)` pays a customer and `client.b2b_payment(...)` pays another business.

---

## 7. Use it in your web app

### Django

```python
# settings.py
INSTALLED_APPS += ["mpesa_tz.contrib.django"]

# urls.py
from django.urls import include, path
urlpatterns += [path("mpesa/", include("mpesa_tz.contrib.django.urls"))]
```

```bash
python manage.py migrate
```

```python
# anywhere in your code, e.g. a view
from mpesa_tz.contrib.django.services import initiate_stk_push

payment = initiate_stk_push("0754123456", 1000, "ORDER1")  # saves a Payment row
print(payment.status)  # "success" or "failed"
```

Payments appear in the Django admin under **M-Pesa Tanzania › Payments**.

### Flask / FastAPI

Ready-to-run examples:

- [`examples/flask_app.py`](examples/flask_app.py): `flask --app examples/flask_app.py run`
- [`examples/fastapi_app.py`](examples/fastapi_app.py): `uvicorn examples.fastapi_app:app --reload`

Both expose `POST /pay` and `POST /mpesa/callback`:

```bash
curl -X POST http://127.0.0.1:5000/pay -H "Content-Type: application/json" \
     -d '{"phone":"000000000001","amount":100,"reference":"ORDER1"}'
```

The stk_push call blocks while waiting for the customer, so in a busy web app run it
in a background worker (Celery, RQ) or a thread.

---

## 8. Go live

1. On the portal, create a **production** application and get its API key, public key and your real shortcode.
2. Update `.env`:
   ```dotenv
   MPESA_ENVIRONMENT=production
   MPESA_API_KEY=...
   MPESA_PUBLIC_KEY=...
   MPESA_SERVICE_PROVIDER_CODE=your-shortcode
   ```
3. Run `mpesa-tz session`, then send one small real payment to your own phone.

In production, only real Tanzanian mobile numbers (`06…`/`07…`) are accepted.

---

## Reference

### What a call returns

Each operation returns an `MpesaResponse` with these fields:

| Field | Meaning |
|---|---|
| `.is_success` | `True` when M-Pesa returned `INS-0` |
| `.code` / `.description` | M-Pesa response code and its message |
| `.transaction_id` | M-Pesa transaction ID |
| `.conversation_id` | M-Pesa conversation ID |
| `.third_party_conversation_id` | Your own ID for the request (generated if you don't pass one) |
| `.raw` | The full JSON M-Pesa sent back |
| `.to_dict()` | All of the above as a dictionary |

### Errors

| Exception | When |
|---|---|
| `MpesaValidationError` | Bad phone, amount or reference (nothing is sent) |
| `MpesaConfigError` | Missing API key, public key or shortcode, or an unknown environment |
| `MpesaConnectionError` | Timeout, DNS or TLS problems |
| `MpesaAuthError` | Invalid API key or not authorised (`INS-2`, `INS-26`) |
| `MpesaAPIError` | Any other `INS-*` error: see `exc.code`, `exc.description`, `exc.response` |

All of them inherit from `MpesaError`. Pass `raise_on_error=False` to the client to get an
unsuccessful `MpesaResponse` back instead of an exception for API errors.
`mpesa_tz.describe("INS-2006")` returns the message for any code.

### Client options

```python
from mpesa_tz import MpesaClient

client = MpesaClient(
    api_key="...",
    public_key="...",
    service_provider_code="000000",
    environment="sandbox",         # or "production"
    timeout=60,                    # seconds to wait for M-Pesa
    session_ttl=3000,              # seconds to reuse a session key
    session_activation_delay=30,   # sandbox: wait for new session keys to activate
    strict_phone=None,             # default: real TZ numbers only in production, relaxed in sandbox
    raise_on_error=True,
)
```

`MpesaClient.from_env(...)` reads the same settings from `MPESA_*` variables, and any
argument you pass to it overrides the environment.

### Async callbacks

If your M-Pesa account sends results to a callback URL, handle them like this in any framework:

```python
from mpesa_tz import parse_callback, callback_ack

result = parse_callback(request_body)      # dict, str or bytes
if result.is_success:
    mark_order_paid(result.third_party_conversation_id, result.transaction_id)
return callback_ack(result)                # the JSON reply M-Pesa expects
```

The Django app already includes this view at `POST /mpesa/callback/`.

### Command line

```bash
mpesa-tz session                                                     # check credentials
mpesa-tz stk-push --phone 0754123456 --amount 1000 --reference ORDER1
mpesa-tz b2c --phone 0754123456 --amount 500 --reference PAY1
mpesa-tz query --reference TX123ABC
mpesa-tz reverse --transaction-id TX123ABC --amount 1000
```

`python -m mpesa_tz ...` works too. Output is JSON, and the exit code is non-zero on failure.

### Upgrading from 0.1.0

`client.stk.push(phone=..., amount=..., reference=...)` still works, but the client now
needs the real credentials:

```python
# 0.1.0
MpesaClient(api_key=..., base_url=...)
# 0.2.0
MpesaClient(api_key=..., public_key=..., service_provider_code=..., environment="sandbox")
```

---

## Common problems

| You see | Fix |
|---|---|
| `MpesaConfigError: api_key is required` | `.env` not found. Run from the folder that contains it, or check that `mpesa-tz[dotenv]` is installed. |
| `Invalid M-Pesa public key` | Paste the **entire** public key from the portal. |
| `INS-2` Invalid API key | Wrong key, or a sandbox key used with `MPESA_ENVIRONMENT=production`. |
| `INS-26` Not authorized | The new session key isn't active yet. Wait about 30 seconds and retry. |
| `INS-13` Invalid shortcode | Check `MPESA_SERVICE_PROVIDER_CODE` (`000000` in the sandbox). |
| `INS-10` Duplicate transaction | Use a new reference each time, e.g. with `generate_reference()`. |
| `INS-5` / `INS-9` | The customer cancelled or didn't answer in time. Let them retry. |
| `MpesaValidationError` | Bad phone, amount or reference. Nothing was sent to M-Pesa. |

More details are in the [troubleshooting section of TESTING.md](TESTING.md#6-troubleshooting).
