# mpesa-tz

A lightweight, developer-friendly Python package for accepting and sending **M-Pesa Tanzania** payments
through the Vodacom M-Pesa OpenAPI.

Works with Django, Flask, FastAPI or plain Python.

## Features

- **STK push**: ask a customer to pay; they confirm with their M-Pesa PIN on their phone
- **Pay customers** (B2C) and **pay other businesses** (B2B)
- **Check a transaction's status** and **reverse** (refund) a payment
- Handles M-Pesa authentication and session keys for you
- Checks phone numbers, amounts and references before anything is sent
- Clear error messages for every M-Pesa response code
- Sandbox (testing) and production modes
- Ready-made Django app: payment records, admin page and callback endpoint
- Command-line tool for quick checks

## Installation

```bash
pip install mpesa-tz
```

Requires Python 3.10+.

## Getting started

**[QUICKSTART.md](https://github.com/aselvicta/Mpesa_integration/blob/main/QUICKSTART.md)** walks you through everything step by step:
getting sandbox credentials, configuring the package, sending your first payment request,
adding it to a Django, Flask or FastAPI app, and going live. It also has the full
technical reference: return values, errors, options, callbacks and CLI commands.

## Documentation

| Guide | What's in it |
|---|---|
| [QUICKSTART.md](https://github.com/aselvicta/Mpesa_integration/blob/main/QUICKSTART.md) | Setup, first payment, framework integration, reference |
| [TESTING.md](https://github.com/aselvicta/Mpesa_integration/blob/main/TESTING.md) | Running the tests and validating the package |
| [CHANGELOG.md](https://github.com/aselvicta/Mpesa_integration/blob/main/CHANGELOG.md) | What changed in each version |
| [examples/](https://github.com/aselvicta/Mpesa_integration/tree/main/examples) | Ready-to-run Python, Flask and FastAPI examples |

## License

MIT
