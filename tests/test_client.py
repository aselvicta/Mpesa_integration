import json

import pytest
import requests
import responses
from responses import matchers

from mpesa_tz import (
    MpesaAPIError,
    MpesaAuthError,
    MpesaClient,
    MpesaConfigError,
    MpesaConnectionError,
    MpesaResponse,
    MpesaValidationError,
)
from mpesa_tz.config import BASE_URLS

from .conftest import (
    B2B_URL, B2C_URL, C2B_URL, QUERY_URL, REVERSAL_URL, SESSION_URL, session_ok, success,
)


# ---------------------------------------------------------------- configuration
def test_requires_api_key(public_key_b64):
    with pytest.raises(MpesaConfigError):
        MpesaClient(api_key="", public_key=public_key_b64)


def test_requires_public_key():
    with pytest.raises(MpesaConfigError):
        MpesaClient(api_key="k")


def test_invalid_public_key():
    with pytest.raises(MpesaConfigError):
        MpesaClient(api_key="k", public_key="garbage")


def test_invalid_environment(public_key_b64):
    with pytest.raises(MpesaConfigError):
        MpesaClient(api_key="k", public_key=public_key_b64, environment="staging")


def test_environment_urls(public_key_b64):
    assert MpesaClient(api_key="k", public_key=public_key_b64).base_url == BASE_URLS["sandbox"]
    prod = MpesaClient(api_key="k", public_key=public_key_b64, environment="PRODUCTION")
    assert prod.base_url == BASE_URLS["production"]
    custom = MpesaClient(api_key="k", public_key=public_key_b64, base_url="https://example.test/api/")
    assert custom.base_url == "https://example.test/api"


def test_from_env(monkeypatch, public_key_b64):
    monkeypatch.setenv("MPESA_API_KEY", "env-key")
    monkeypatch.setenv("MPESA_PUBLIC_KEY", public_key_b64)
    monkeypatch.setenv("MPESA_SERVICE_PROVIDER_CODE", "123456")
    monkeypatch.setenv("MPESA_ENVIRONMENT", "production")
    monkeypatch.setenv("MPESA_TIMEOUT", "15")
    c = MpesaClient.from_env(load_dotenv=False)
    assert (c.api_key, c.service_provider_code, c.environment, c.timeout) == ("env-key", "123456", "production", 15.0)
    assert MpesaClient.from_env(load_dotenv=False, service_provider_code="999").service_provider_code == "999"


def test_from_env_missing(monkeypatch):
    for name in ("MPESA_API_KEY", "MPESA_PUBLIC_KEY"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(MpesaConfigError):
        MpesaClient.from_env(load_dotenv=False)


# ---------------------------------------------------------------- session
def test_session_key_request(client, mocked, decrypt):
    mocked.add(responses.GET, SESSION_URL, json=session_ok("ABC"))
    assert client.get_session_key() == "ABC"
    req = mocked.calls[0].request
    assert decrypt(req.headers["Authorization"]) == "test-api-key"
    assert req.headers["Origin"] == "*"


def test_session_key_is_cached(client, mocked):
    mocked.add(responses.GET, SESSION_URL, json=session_ok("ABC"))
    client.get_session_key()
    client.get_session_key()
    assert len(mocked.calls) == 1


def test_session_key_expires(client, mocked):
    client.session_ttl = 0
    mocked.add(responses.GET, SESSION_URL, json=session_ok("A"))
    mocked.add(responses.GET, SESSION_URL, json=session_ok("B"))
    assert client.get_session_key() == "A"
    assert client.get_session_key() == "B"


def test_session_force_refresh_and_invalidate(client, mocked):
    mocked.add(responses.GET, SESSION_URL, json=session_ok("A"))
    mocked.add(responses.GET, SESSION_URL, json=session_ok("B"))
    mocked.add(responses.GET, SESSION_URL, json=session_ok("C"))
    client.get_session_key()
    assert client.get_session_key(force_refresh=True) == "B"
    client.invalidate_session()
    assert client.get_session_key() == "C"


def test_session_invalid_api_key(client, mocked):
    mocked.add(responses.GET, SESSION_URL, status=401,
               json={"output_ResponseCode": "INS-2", "output_ResponseDesc": "Invalid API key"})
    with pytest.raises(MpesaAuthError) as exc:
        client.get_session_key()
    assert exc.value.code == "INS-2" and exc.value.status_code == 401


def test_session_activation_delay(client, mocked, monkeypatch):
    slept = []
    monkeypatch.setattr("mpesa_tz.client.time.sleep", slept.append)
    client.session_activation_delay = 3
    mocked.add(responses.GET, SESSION_URL, json=session_ok())
    client.get_session_key()
    assert slept == [3]


# ---------------------------------------------------------------- c2b / stk push
def test_stk_push_success(client, mocked, decrypt):
    mocked.add(responses.GET, SESSION_URL, json=session_ok("SESSION-XYZ"))
    mocked.add(responses.POST, C2B_URL, json=success())
    result = client.stk_push("0754123456", 1000, "ORDER1", "Shoes", conversation_id="conv1")

    assert isinstance(result, MpesaResponse)
    assert result.is_success and result.transaction_id == "TX123" and result.conversation_id == "CONV123"
    assert result["output_TransactionID"] == "TX123" and result.get("missing", 1) == 1

    req = mocked.calls[1].request
    assert decrypt(req.headers["Authorization"]) == "SESSION-XYZ"
    assert json.loads(req.body) == {
        "input_Amount": "1000",
        "input_Country": "TZN",
        "input_Currency": "TZS",
        "input_CustomerMSISDN": "255754123456",
        "input_ServiceProviderCode": "000000",
        "input_ThirdPartyConversationID": "conv1",
        "input_TransactionReference": "ORDER1",
        "input_PurchasedItemsDesc": "Shoes",
    }


def test_stk_push_generates_conversation_id(client, mocked):
    mocked.add(responses.GET, SESSION_URL, json=session_ok())
    mocked.add(responses.POST, C2B_URL, json=success())
    client.c2b_payment("0754123456", 500, "R1")
    assert len(json.loads(mocked.calls[1].request.body)["input_ThirdPartyConversationID"]) == 32


def test_legacy_stk_interface(client, mocked):
    """0.1.x API: client.stk.push(phone, amount, reference)."""
    mocked.add(responses.GET, SESSION_URL, json=session_ok())
    mocked.add(responses.POST, C2B_URL, json=success())
    assert client.stk.push(phone="0754123456", amount=5000, reference="ORDER1").is_success


@pytest.mark.parametrize("code,desc", [
    ("INS-5", "Transaction cancelled by customer"),
    ("INS-2006", "Insufficient balance"),
    ("INS-10", "Duplicate transaction"),
])
def test_stk_push_api_error(client, mocked, code, desc):
    mocked.add(responses.GET, SESSION_URL, json=session_ok())
    mocked.add(responses.POST, C2B_URL, status=422,
               json={"output_ResponseCode": code, "output_ResponseDesc": desc})
    with pytest.raises(MpesaAPIError) as exc:
        client.stk_push("0754123456", 1000, "ORDER1")
    assert not isinstance(exc.value, MpesaAuthError)
    assert exc.value.code == code and exc.value.description == desc and exc.value.status_code == 422
    assert exc.value.response["output_ResponseCode"] == code


def test_raise_on_error_false_returns_response(client, mocked):
    client.raise_on_error = False
    mocked.add(responses.GET, SESSION_URL, json=session_ok())
    mocked.add(responses.POST, C2B_URL, status=400,
               json={"output_ResponseCode": "INS-5", "output_ResponseDesc": "Cancelled"})
    result = client.stk_push("0754123456", 1000, "ORDER1")
    assert not result.is_success and result.code == "INS-5" and result.status_code == 400


def test_expired_session_is_refreshed_once(client, mocked, decrypt):
    mocked.add(responses.GET, SESSION_URL, json=session_ok("OLD"))
    mocked.add(responses.POST, C2B_URL, status=401,
               json={"output_ResponseCode": "INS-26", "output_ResponseDesc": "Not authorized"})
    mocked.add(responses.GET, SESSION_URL, json=session_ok("NEW"))
    mocked.add(responses.POST, C2B_URL, json=success())

    assert client.stk_push("0754123456", 1000, "ORDER1").is_success
    assert decrypt(mocked.calls[3].request.headers["Authorization"]) == "NEW"
    assert len(mocked.calls) == 4


def test_auth_error_after_retry_raises(client, mocked):
    mocked.add(responses.GET, SESSION_URL, json=session_ok())
    mocked.add(responses.POST, C2B_URL, status=401,
               json={"output_ResponseCode": "INS-26", "output_ResponseDesc": "Not authorized"})
    with pytest.raises(MpesaAuthError):
        client.stk_push("0754123456", 1000, "ORDER1")
    assert len(mocked.calls) == 4  # session, call, session, call - no infinite loop


def test_non_json_response(client, mocked):
    mocked.add(responses.GET, SESSION_URL, json=session_ok())
    mocked.add(responses.POST, C2B_URL, status=502, body="<html>Bad gateway</html>")
    with pytest.raises(MpesaAPIError) as exc:
        client.stk_push("0754123456", 1000, "ORDER1")
    assert exc.value.status_code == 502


def test_json_array_response(client, mocked):
    mocked.add(responses.GET, SESSION_URL, json=[1, 2])
    with pytest.raises(MpesaAPIError):
        client.get_session_key()


def test_timeout(client, mocked):
    mocked.add(responses.GET, SESSION_URL, json=session_ok())
    mocked.add(responses.POST, C2B_URL, body=requests.Timeout("slow"))
    with pytest.raises(MpesaConnectionError):
        client.stk_push("0754123456", 1000, "ORDER1")


def test_connection_error(client, mocked):
    mocked.add(responses.GET, SESSION_URL, body=requests.ConnectionError("dns"))
    with pytest.raises(MpesaConnectionError):
        client.get_session_key()


@pytest.mark.parametrize("phone,amount,ref", [
    ("12345", 1000, "ORDER1"),
    ("0754123456", 0, "ORDER1"),
    ("0754123456", 1000, "BAD REF"),
])
def test_validation_happens_before_network(client, mocked, phone, amount, ref):
    with pytest.raises(MpesaValidationError):
        client.stk_push(phone, amount, ref)
    assert len(mocked.calls) == 0


def test_missing_shortcode(public_key_b64, mocked):
    c = MpesaClient(api_key="k", public_key=public_key_b64)
    with pytest.raises(MpesaConfigError):
        c.stk_push("0754123456", 1000, "ORDER1")


# ---------------------------------------------------------------- other operations
def test_b2c_payment(client, mocked):
    mocked.add(responses.GET, SESSION_URL, json=session_ok())
    mocked.add(responses.POST, B2C_URL, json=success())
    assert client.b2c_payment("+255 654 123 456", "250.50", "PAYOUT1", "Refund").is_success
    body = json.loads(mocked.calls[1].request.body)
    assert body["input_CustomerMSISDN"] == "255654123456"
    assert body["input_Amount"] == "250.50"
    assert body["input_PaymentItemsDesc"] == "Refund"


def test_b2b_payment(client, mocked):
    mocked.add(responses.GET, SESSION_URL, json=session_ok())
    mocked.add(responses.POST, B2B_URL, json=success())
    assert client.b2b_payment("888888", 10000, "INV1").is_success
    body = json.loads(mocked.calls[1].request.body)
    assert body["input_PrimaryPartyCode"] == "000000" and body["input_ReceiverPartyCode"] == "888888"
    with pytest.raises(MpesaValidationError):
        client.b2b_payment("", 1, "INV1")


def test_query_transaction_status(client, mocked):
    mocked.add(responses.GET, SESSION_URL, json=session_ok())
    mocked.add(
        responses.GET, QUERY_URL,
        json=success(output_ResponseTransactionStatus="Completed"),
        match=[matchers.query_param_matcher({
            "input_QueryReference": "TX123",
            "input_ServiceProviderCode": "000000",
            "input_ThirdPartyConversationID": "q1",
            "input_Country": "TZN",
        })],
    )
    result = client.query_transaction_status("TX123", conversation_id="q1")
    assert result.get("output_ResponseTransactionStatus") == "Completed"
    with pytest.raises(MpesaValidationError):
        client.query_transaction_status("")


def test_reversal(client, mocked):
    mocked.add(responses.GET, SESSION_URL, json=session_ok())
    mocked.add(responses.PUT, REVERSAL_URL, json=success())
    assert client.reversal("TX123", 1000).is_success
    body = json.loads(mocked.calls[1].request.body)
    assert body["input_TransactionID"] == "TX123" and body["input_ReversalAmount"] == "1000"
    with pytest.raises(MpesaValidationError):
        client.reversal("", 1000)


def test_response_to_dict_and_repr(client):
    r = MpesaResponse.from_payload(success())
    d = r.to_dict()
    assert d["is_success"] and d["transaction_id"] == "TX123"
    assert r.code_description == "Request processed successfully"
    assert "sandbox" in repr(client)


def test_strict_phone_defaults(public_key_b64):
    assert MpesaClient(api_key="k", public_key=public_key_b64).strict_phone is False
    assert MpesaClient(api_key="k", public_key=public_key_b64, environment="production").strict_phone is True
    assert MpesaClient(api_key="k", public_key=public_key_b64, strict_phone=True).strict_phone is True


def test_production_rejects_sandbox_msisdn(public_key_b64, mocked):
    c = MpesaClient(api_key="k", public_key=public_key_b64, service_provider_code="1", environment="production")
    with pytest.raises(MpesaValidationError):
        c.stk_push("000000000001", 100, "R1")
