import pytest

from mpesa_tz import MpesaConfigError
from mpesa_tz.crypto import encrypt, load_public_key


def test_encrypt_roundtrip_base64_key(public_key_b64, decrypt):
    assert decrypt("Bearer " + encrypt("hello", public_key_b64)) == "hello"


def test_encrypt_roundtrip_pem_key(public_key_pem, decrypt):
    assert decrypt("Bearer " + encrypt("hello", public_key_pem)) == "hello"


def test_key_with_whitespace_and_bytes(public_key_b64, decrypt):
    wrapped = "\n".join(public_key_b64[i:i + 64] for i in range(0, len(public_key_b64), 64))
    assert decrypt("Bearer " + encrypt("x", wrapped.encode())) == "x"


def test_encryption_is_randomised(public_key_b64):
    assert encrypt("same", public_key_b64) != encrypt("same", public_key_b64)


@pytest.mark.parametrize("bad", [None, "", "not-a-key", "aGVsbG8="])
def test_invalid_key(bad):
    with pytest.raises(MpesaConfigError):
        load_public_key(bad)


def test_encrypt_empty_value(public_key_b64):
    with pytest.raises(MpesaConfigError):
        encrypt("", public_key_b64)
