import base64

import pytest
import responses as responses_lib
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from mpesa_tz import MpesaClient
from mpesa_tz.config import BASE_URLS, ENDPOINTS

BASE = BASE_URLS["sandbox"]
SESSION_URL = BASE + ENDPOINTS["session"]
C2B_URL = BASE + ENDPOINTS["c2b"]
B2C_URL = BASE + ENDPOINTS["b2c"]
B2B_URL = BASE + ENDPOINTS["b2b"]
QUERY_URL = BASE + ENDPOINTS["query"]
REVERSAL_URL = BASE + ENDPOINTS["reversal"]


@pytest.fixture(scope="session")
def private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def public_key_b64(private_key):
    der = private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return base64.b64encode(der).decode()


@pytest.fixture(scope="session")
def public_key_pem(private_key):
    return private_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()


@pytest.fixture
def decrypt(private_key):
    def _decrypt(bearer_header):
        token = bearer_header.split(" ", 1)[1]
        return private_key.decrypt(base64.b64decode(token), padding.PKCS1v15()).decode()

    return _decrypt


@pytest.fixture
def client(public_key_b64):
    return MpesaClient(
        api_key="test-api-key",
        public_key=public_key_b64,
        service_provider_code="000000",
        environment="sandbox",
    )


@pytest.fixture
def mocked():
    with responses_lib.RequestsMock() as rsps:
        yield rsps


def session_ok(session_id="SESSION123"):
    return {"output_ResponseCode": "INS-0", "output_ResponseDesc": "Request processed successfully",
            "output_SessionID": session_id}


def success(**extra):
    body = {
        "output_ResponseCode": "INS-0",
        "output_ResponseDesc": "Request processed successfully",
        "output_TransactionID": "TX123",
        "output_ConversationID": "CONV123",
        "output_ThirdPartyConversationID": "TP123",
    }
    body.update(extra)
    return body


@pytest.fixture
def client_django():
    from django.test import Client

    return Client()
