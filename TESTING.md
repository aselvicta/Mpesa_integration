# Testing & validating `mpesa-tz`

This guide covers validating the package at every level:

1. [Automated unit tests](#1-automated-unit-tests) – offline, no credentials needed
2. [Package build validation](#2-package-build-validation) – does the wheel build, install and import cleanly?
3. [Live sandbox tests](#3-live-sandbox-tests) – real calls to the M-Pesa OpenAPI sandbox
4. [Framework integration checks](#4-framework-integration-checks) – Django, Flask, callbacks
5. [Release checklist](#5-release-checklist)
6. [Troubleshooting](#6-troubleshooting)

---

## 0. Setup

```bash
git clone https://github.com/aselvicta/Mpesa_integration.git
cd Mpesa_integration
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

`[dev]` installs pytest, pytest-cov, responses (HTTP mocking), Django, pytest-django, build and twine.

---

## 1. Automated unit tests

```bash
pytest                                            # all offline tests
pytest --cov=mpesa_tz --cov-report=term-missing   # with coverage
pytest tests/test_client.py -v                    # one file, verbose
pytest -k stk_push                                # tests matching a name
```

**Expected result:** `104 passed, 2 skipped`, coverage ≈ 98%.
The 2 skipped tests are the live sandbox tests (section 3).

The offline tests never touch the network. HTTP is mocked with `responses`, and a
throw-away RSA key pair is generated per run, so the tests can **decrypt** the bearer
tokens and check that the encryption is correct.

### What is covered

| File | Validates |
|---|---|
| `tests/test_utils.py` | Phone normalisation (`0754…`, `754…`, `+255 754…`, `255-754-…`), invalid numbers, sandbox MSISDNs, amount formatting (`1000`, `10.50`, rejects `0`, negatives, `NaN`, >2 decimals, booleans), reference rules (1–20 alphanumeric), unique id generation, `INS-*` descriptions |
| `tests/test_crypto.py` | RSA PKCS#1 v1.5 encryption round-trip with base64-DER and PEM keys, wrapped/bytes keys, invalid keys, randomised ciphertext |
| `tests/test_client.py` | Config errors, sandbox/production/custom URLs, `from_env`, session key request (encrypted API key + `Origin` header), session caching/expiry/refresh, invalid API key, sandbox activation delay, exact C2B request body, encrypted session bearer, legacy `client.stk.push`, API errors (`INS-5`, `INS-2006`, `INS-10`), `raise_on_error=False`, **automatic session refresh + single retry** (no infinite loop), non-JSON responses, timeouts, connection errors, validation before any network call, B2C, B2B, status query params, reversal (PUT) |
| `tests/test_callbacks_cli.py` | Callback parsing from dict/str/bytes, invalid callbacks, acknowledgement body, public exports, CLI success/error exit codes, missing config |
| `tests/test_django.py` | Migrations match models, `initiate_stk_push` stores success/failure, B2C service, callback view updates `Payment`, unknown/invalid callbacks, `405` on GET, settings-based client, admin registration |
| `tests/test_live_sandbox.py` | Real sandbox session + STK push (opt-in) |

---

## 2. Package build validation

Check that the distributable package itself works, not just the source tree.

```bash
# 2.1 Build sdist + wheel and validate metadata / README rendering for PyPI
rm -rf dist build *.egg-info
python -m build
twine check dist/*
```

**Expected:** `Checking dist/mpesa_tz-0.2.0-py3-none-any.whl: PASSED` (and the same for the `.tar.gz`).

```bash
# 2.2 Inspect the wheel - it must contain mpesa_tz/ and the Django migrations, and no tests/
unzip -l dist/mpesa_tz-0.2.0-py3-none-any.whl
```

```bash
# 2.3 Install into a clean virtualenv (no Django!) and import from outside the repo
python3 -m venv /tmp/mpesa-clean
/tmp/mpesa-clean/bin/pip install dist/mpesa_tz-0.2.0-py3-none-any.whl
cd /tmp
/tmp/mpesa-clean/bin/python -c "
import sys, mpesa_tz
from mpesa_tz import MpesaClient, normalize_phone
print('version', mpesa_tz.__version__)
print('phone', normalize_phone('0754 123 456'))
print('django imported:', 'django' in sys.modules)
"
/tmp/mpesa-clean/bin/mpesa-tz --version
```

**Expected:**

```
version 0.2.0
phone 255754123456
django imported: False
mpesa-tz 0.2.0
```

`django imported: False` shows the core package doesn't depend on Django. In 0.1.0,
`import mpesa_tz` failed because of this.

```bash
# 2.4 Optional: verify the upload on TestPyPI before the real PyPI
twine upload --repository testpypi dist/*
pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ mpesa-tz==0.2.0
```

---

## 3. Live sandbox tests

These tests make **real** HTTP calls to `https://openapi.m-pesa.com/sandbox/...`.

### 3.1 Get sandbox credentials

1. Register at <https://openapiportal.m-pesa.com>.
2. Create an application and select the **Vodacom Tanzania** market and the **sandbox** environment.
3. Copy the **API key** and the sandbox **public key**.
4. Note the sandbox **service provider code** (usually `000000`) and the **test MSISDN** listed in the portal's API documentation (e.g. `000000000001`).

### 3.2 Configure

```bash
cp .env.example .env
# edit .env:
#   MPESA_API_KEY=...
#   MPESA_PUBLIC_KEY=...
#   MPESA_SERVICE_PROVIDER_CODE=000000
#   MPESA_ENVIRONMENT=sandbox
#   MPESA_TEST_PHONE=000000000001
```

`.env` is git-ignored. **Never commit credentials.**

### 3.3 Step-by-step with the CLI

```bash
# a) Credentials + encryption + session key
mpesa-tz session
```
Expected: `{"ok": true, "message": "Session key obtained", "environment": "sandbox"}`

New sandbox session keys can take up to ~30 seconds to activate. Wait before the next step.
In code, use `MpesaClient(..., session_activation_delay=30)` for this.

```bash
# b) STK push / C2B
mpesa-tz stk-push --phone 000000000001 --amount 100 --reference TEST001
```
Expected: `"code": "INS-0"`, `"is_success": true`, plus a `transaction_id`.

```bash
# c) Query the transaction (use transaction_id from b)
mpesa-tz query --reference <transaction_id>

# d) B2C
mpesa-tz b2c --phone 000000000001 --amount 100 --reference TEST002

# e) Reversal (use a transaction_id from b or d)
mpesa-tz reverse --transaction-id <transaction_id> --amount 100

# f) Error handling: a duplicate reference / bad amount should give a clean JSON error, exit code 1
mpesa-tz stk-push --phone 000000000001 --amount 0 --reference TEST003; echo "exit=$?"
```

### 3.4 Run the live pytest suite

```bash
export $(grep -v '^#' .env | xargs)     # or rely on the .env loader
MPESA_LIVE_TESTS=1 pytest -m live -v
```

`MPESA_SESSION_DELAY` (default `30`) controls the wait after a session key is created.

**Expected:** `test_live_session PASSED`, `test_live_stk_push PASSED`.

### 3.5 Production smoke test (before go-live)

Set `MPESA_ENVIRONMENT=production` with the production API key, public key and shortcode.
Then run `mpesa-tz session` and **one** small real STK push to your own phone, e.g. 100 TZS.
Confirm that the PIN prompt arrives and the SMS receipt matches `transaction_id`.
Reverse it afterwards if you need to.
Production phone validation is strict, so `000000000001` is rejected there, as intended.

---

## 4. Framework integration checks

### 4.1 Django

In a throw-away Django project:

```bash
pip install -e "/path/to/Mpesa_integration[django,dotenv]"
django-admin startproject demo && cd demo
```

`demo/settings.py`:

```python
INSTALLED_APPS += ["mpesa_tz.contrib.django"]
MPESA_TZ = {"ENVIRONMENT": "sandbox"}   # remaining values from MPESA_* env / .env
```

`demo/urls.py`:

```python
from django.urls import include, path
urlpatterns += [path("mpesa/", include("mpesa_tz.contrib.django.urls"))]
```

```bash
python manage.py migrate                       # creates mpesa_tz_payment
python manage.py makemigrations --check        # expected: "No changes detected"
python manage.py shell -c "
from mpesa_tz.contrib.django.services import initiate_stk_push
p = initiate_stk_push('000000000001', 100, 'DJTEST1')
print(p.status, p.transaction_id)
"
python manage.py createsuperuser && python manage.py runserver
```

- Open `/admin/` and check that the **M-Pesa Tanzania › Payments** row exists.
- Simulate a callback (in another terminal):

```bash
curl -X POST http://127.0.0.1:8000/mpesa/callback/ \
  -H "Content-Type: application/json" \
  -d '{"input_OriginalConversationID":"CONV1","input_TransactionID":"TX1",
       "input_ResultCode":"INS-0","input_ResultDesc":"OK",
       "input_ThirdPartyConversationID":"<third_party_conversation_id of a Payment>"}'
```

Expected response: `{"output_OriginalConversationID": "CONV1", "output_ResponseCode": "0", ...}`.
The Payment row should now be `success` with transaction id `TX1`.
A `GET` to the same URL should return `405`, and invalid JSON should return `400`.

### 4.2 Flask

```bash
pip install flask "mpesa-tz[dotenv]"
flask --app examples/flask_app.py run
curl -X POST http://127.0.0.1:5000/pay -H "Content-Type: application/json" \
     -d '{"phone":"000000000001","amount":100,"reference":"FLASK1"}'
curl -X POST http://127.0.0.1:5000/pay -H "Content-Type: application/json" \
     -d '{"phone":"abc","amount":100,"reference":"FLASK2"}'      # expect 400
```

### 4.3 FastAPI

```bash
pip install fastapi uvicorn "mpesa-tz[dotenv]"
uvicorn examples.fastapi_app:app --reload
# then POST to http://127.0.0.1:8000/pay as above, or use http://127.0.0.1:8000/docs
```

### 4.4 Exposing a callback URL for sandbox testing

```bash
ngrok http 8000      # use the https URL + /mpesa/callback/ in the portal configuration
```

---

## 5. Release checklist

- [ ] `pytest --cov=mpesa_tz` shows all green, coverage ≥ 95%
- [ ] GitHub Actions `tests` workflow is green on all Python versions
- [ ] `python -m build && twine check dist/*` shows PASSED
- [ ] Clean-venv install works and `django imported: False` (section 2.3)
- [ ] `mpesa-tz session` and `mpesa-tz stk-push` succeed in the sandbox
- [ ] `MPESA_LIVE_TESTS=1 pytest -m live` passes
- [ ] Django `makemigrations --check` reports no changes
- [ ] Version bumped in **both** `pyproject.toml` and `mpesa_tz/__init__.py`; `CHANGELOG.md` updated
- [ ] `.env` is not committed (`git status` is clean of secrets)
- [ ] Push a version tag (`git tag v<version> && git push origin v<version>`). The `publish` workflow tests, builds and uploads to PyPI through Trusted Publishing.
- [ ] `pip install mpesa-tz==<version>` from PyPI in a clean venv works

---

## 6. Troubleshooting

| Symptom / code | Likely cause | Fix |
|---|---|---|
| `MpesaConfigError: Invalid M-Pesa public key` | Key copied incompletely or with extra characters | Paste the whole key from the portal. Base64 or PEM both work. |
| `INS-2` Invalid API key | Wrong key, or sandbox key used against production | Check `MPESA_API_KEY` and `MPESA_ENVIRONMENT` |
| `INS-26` Not authorized right after `session` | Sandbox session not yet active | Use `session_activation_delay=30`. The client also refreshes and retries once on its own. |
| `INS-13` Invalid shortcode | Wrong `MPESA_SERVICE_PROVIDER_CODE` | Use the portal's sandbox shortcode (`000000`) |
| `INS-10` Duplicate transaction | Reference / conversation id reused | Use `generate_reference()` |
| `INS-17` Invalid reference | Reference > 20 chars or not alphanumeric | Rejected locally as `MpesaValidationError` |
| `INS-5` / `INS-9` | Customer cancelled / didn't answer in time | Normal business outcome. Let the customer retry. |
| `INS-2006` | Insufficient balance | – |
| `MpesaConnectionError` | Network / timeout | Increase `timeout`. Query the transaction before retrying a payment. |
| HTTP 403 / CORS errors | `Origin` header doesn't match the portal | Set `MPESA_ORIGIN` to the value configured in the portal |
| `pytest`: "pytest-django could not find a Django project" | Running from a different directory | Run `pytest` from the repo root |

The full code list is in `mpesa_tz/codes.py` (`mpesa_tz.describe("INS-xxx")`).
