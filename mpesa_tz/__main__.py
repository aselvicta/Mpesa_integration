"""Command line helper for quick sandbox checks.

Configuration is read from MPESA_* environment variables (or a .env file):

    python -m mpesa_tz session
    python -m mpesa_tz stk-push --phone 0754123456 --amount 1000 --reference ORDER1
    python -m mpesa_tz b2c --phone 0754123456 --amount 500 --reference PAYOUT1
    python -m mpesa_tz query --reference <transaction or conversation id>
    python -m mpesa_tz reverse --transaction-id <id> --amount 1000
"""

import argparse
import json
import sys

from . import __version__
from .client import MpesaClient
from .exceptions import MpesaAPIError, MpesaError


def _build_parser():
    parser = argparse.ArgumentParser(prog="python -m mpesa_tz", description="M-Pesa Tanzania CLI")
    parser.add_argument("--version", action="version", version="mpesa-tz " + __version__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("session", help="Obtain a session key (checks credentials)")

    for name, help_text in (("stk-push", "Prompt a customer to pay (C2B)"), ("b2c", "Pay a customer (B2C)")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--phone", required=True)
        p.add_argument("--amount", required=True)
        p.add_argument("--reference", required=True)
        p.add_argument("--description", default="Payment")

    p = sub.add_parser("query", help="Query a transaction status")
    p.add_argument("--reference", required=True)

    p = sub.add_parser("reverse", help="Reverse a transaction")
    p.add_argument("--transaction-id", required=True)
    p.add_argument("--amount", required=True)
    return parser


def main(argv=None, client=None):
    args = _build_parser().parse_args(argv)
    try:
        client = client or MpesaClient.from_env()
        if args.command == "session":
            client.get_session_key()
            out = {"ok": True, "message": "Session key obtained", "environment": client.environment}
        elif args.command == "stk-push":
            out = client.c2b_payment(args.phone, args.amount, args.reference, args.description).to_dict()
        elif args.command == "b2c":
            out = client.b2c_payment(args.phone, args.amount, args.reference, args.description).to_dict()
        elif args.command == "query":
            out = client.query_transaction_status(args.reference).to_dict()
        else:
            out = client.reversal(args.transaction_id, args.amount).to_dict()
    except MpesaError as exc:
        err = {"ok": False, "error": type(exc).__name__, "message": str(exc)}
        if isinstance(exc, MpesaAPIError):
            err.update(code=exc.code, response=exc.response)
        print(json.dumps(err, indent=2))
        return 1
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
