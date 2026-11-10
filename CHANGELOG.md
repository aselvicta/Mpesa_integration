# Changelog

## 0.2.0

First working release. 0.1.0 on PyPI was not importable
(`from mpesa_tz import MpesaClient` failed, `stk.push` called a missing
`get_headers`, and `models.py` required Django and crashed on import).

- Real Vodacom Tanzania M-Pesa OpenAPI integration (RSA-encrypted API key -> session key -> encrypted session bearer).
- `MpesaClient` with `stk_push`/`c2b_payment`, `b2c_payment`, `b2b_payment`, `query_transaction_status`, `reversal`.
- Session key caching with automatic refresh and one retry on auth errors.
- Phone / amount / reference validation, typed exceptions, `INS-*` code descriptions.
- `MpesaClient.from_env()` (+ optional `.env` support).
- Callback parsing + acknowledgement helpers.
- Optional Django app `mpesa_tz.contrib.django` (Payment model, admin, callback view, services).
- CLI: `python -m mpesa_tz` / `mpesa-tz`.
- `client.stk.push(phone, amount, reference)` from 0.1.x still works.
- Breaking: `MpesaClient(api_key, base_url)` now also needs `public_key` and `service_provider_code`.
