"""Input normalisation / validation helpers."""

import re
import uuid
from decimal import Decimal, InvalidOperation

from .exceptions import MpesaValidationError

_TZ_MOBILE = re.compile(r"^255[67]\d{8}$")
_REFERENCE = re.compile(r"^[A-Za-z0-9]{1,20}$")


def normalize_phone(phone, strict=True):
    """Normalise a Tanzanian mobile number to ``2557XXXXXXXX`` / ``2556XXXXXXXX``.

    Accepts ``0754123456``, ``754123456``, ``+255 754 123 456``,
    ``255-754-123-456`` and ``255754123456``.

    With ``strict=False`` any 9-15 digit number is accepted after the same
    clean-up (needed for sandbox test MSISDNs such as ``000000000001``).
    """
    if phone is None:
        raise MpesaValidationError("Phone number is required")
    digits = re.sub(r"[\s\-().]", "", str(phone))
    if digits.startswith("+"):
        digits = digits[1:]
    if not digits.isdigit():
        raise MpesaValidationError("Invalid phone number: %r" % phone)
    if not strict and 9 <= len(digits) <= 15 and not _looks_local(digits):
        return digits
    if _looks_local(digits) and digits.startswith("0"):
        digits = "255" + digits[1:]
    elif _looks_local(digits):
        digits = "255" + digits
    if not _TZ_MOBILE.match(digits):
        raise MpesaValidationError("Invalid Tanzanian mobile number: %r" % phone)
    return digits


def _looks_local(digits):
    """True for local formats like 0754123456 / 754123456."""
    return (len(digits) == 10 and digits[0] == "0" and digits[1] in "67") or (
        len(digits) == 9 and digits[0] in "67"
    )


def format_amount(amount):
    """Validate an amount and return it as the string the API expects."""
    if isinstance(amount, bool):
        raise MpesaValidationError("Invalid amount: %r" % amount)
    try:
        value = Decimal(str(amount).strip())
    except (InvalidOperation, ValueError):
        raise MpesaValidationError("Invalid amount: %r" % amount)
    if not value.is_finite() or value <= 0:
        raise MpesaValidationError("Amount must be greater than zero, got %r" % amount)
    if value != value.quantize(Decimal("0.01")):
        raise MpesaValidationError("Amount can have at most 2 decimal places: %r" % amount)
    if value == value.to_integral_value():
        return str(int(value))
    return "{:.2f}".format(value)


def validate_reference(reference, field="reference"):
    """References must be 1-20 alphanumeric characters (API rule, INS-17)."""
    if reference is None or not _REFERENCE.match(str(reference)):
        raise MpesaValidationError(
            "%s must be 1-20 alphanumeric characters, got %r" % (field, reference)
        )
    return str(reference)


def generate_conversation_id():
    """Generate a unique third-party conversation id (32 hex chars)."""
    return uuid.uuid4().hex


def generate_reference(prefix="T"):
    """Generate a unique alphanumeric transaction reference (<= 20 chars)."""
    prefix = re.sub(r"[^A-Za-z0-9]", "", prefix)[:8]
    return (prefix + uuid.uuid4().hex.upper())[:20]
