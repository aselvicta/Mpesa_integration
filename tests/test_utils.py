import pytest

from mpesa_tz import MpesaValidationError, describe, format_amount, generate_reference, normalize_phone
from mpesa_tz.utils import generate_conversation_id, validate_reference


@pytest.mark.parametrize("raw", [
    "0754123456", "754123456", "255754123456", "+255754123456", "+255 754 123 456",
    "255-754-123-456", "(0754) 123456", 255754123456,
])
def test_normalize_phone_valid(raw):
    assert normalize_phone(raw) == "255754123456"


def test_normalize_phone_6x_prefix():
    assert normalize_phone("0654123456") == "255654123456"


@pytest.mark.parametrize("raw", [None, "", "abc", "07541234", "254712345678", "0854123456", "07541234567", "+"])
def test_normalize_phone_invalid(raw):
    with pytest.raises(MpesaValidationError):
        normalize_phone(raw)


@pytest.mark.parametrize("raw,expected", [
    (1000, "1000"), ("1000", "1000"), (1000.0, "1000"), ("10.5", "10.50"), (10.25, "10.25"), ("1e3", "1000"),
])
def test_format_amount_valid(raw, expected):
    assert format_amount(raw) == expected


@pytest.mark.parametrize("raw", [0, -5, "abc", None, "10.123", True, "nan", "inf", ""])
def test_format_amount_invalid(raw):
    with pytest.raises(MpesaValidationError):
        format_amount(raw)


def test_validate_reference():
    assert validate_reference("ORDER1") == "ORDER1"
    for bad in ["", None, "has space", "x" * 21, "ORDER-1"]:
        with pytest.raises(MpesaValidationError):
            validate_reference(bad)


def test_generated_ids_are_unique_and_valid():
    refs = {generate_reference("ORDER") for _ in range(500)}
    assert len(refs) == 500
    for ref in refs:
        assert validate_reference(ref) and ref.startswith("ORDER") and len(ref) == 20
    assert generate_reference("a-b c").startswith("abc")
    assert generate_conversation_id() != generate_conversation_id()


def test_describe_codes():
    assert describe("INS-0") == "Request processed successfully"
    assert describe("INS-2006") == "Insufficient balance"
    assert describe("NOPE") == "Unknown response code"


def test_normalize_phone_non_strict_allows_sandbox_numbers():
    assert normalize_phone("000000000001", strict=False) == "000000000001"
    assert normalize_phone("0754123456", strict=False) == "255754123456"  # still normalised
    with pytest.raises(MpesaValidationError):
        normalize_phone("000000000001")  # strict by default
    with pytest.raises(MpesaValidationError):
        normalize_phone("1234", strict=False)
