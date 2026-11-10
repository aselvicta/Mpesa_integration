"""RSA helpers used to build the M-Pesa OpenAPI bearer tokens.

The OpenAPI requires the API key (and later the session key) to be encrypted
with the public key from the developer portal using RSA PKCS#1 v1.5 and then
base64 encoded.
"""

import base64
import re

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

from .exceptions import MpesaConfigError

_PEM_HEADER = re.compile(r"-----(BEGIN|END) (RSA )?PUBLIC KEY-----")


def load_public_key(public_key):
    """Load a public key given as base64 DER (portal format) or PEM text/bytes."""
    if not public_key:
        raise MpesaConfigError("A public key is required")
    if isinstance(public_key, bytes):
        public_key = public_key.decode("utf-8")

    text = public_key.strip()
    try:
        if text.startswith("-----BEGIN"):
            return serialization.load_pem_public_key(text.encode("utf-8"))
        der = base64.b64decode("".join(_PEM_HEADER.sub("", text).split()), validate=True)
        return serialization.load_der_public_key(der)
    except Exception as exc:  # cryptography raises several types
        raise MpesaConfigError("Invalid M-Pesa public key: %s" % exc) from exc


def encrypt(value, public_key):
    """Encrypt ``value`` with ``public_key`` and return a base64 string."""
    if not value:
        raise MpesaConfigError("Cannot encrypt an empty value")
    key = public_key if hasattr(public_key, "encrypt") else load_public_key(public_key)
    cipher = key.encrypt(value.encode("utf-8"), padding.PKCS1v15())
    return base64.b64encode(cipher).decode("ascii")
