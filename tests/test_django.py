import json
from io import StringIO

import pytest

pytest.importorskip("django")
pytest.importorskip("pytest_django")

import responses  # noqa: E402
from django.core.management import call_command  # noqa: E402

from mpesa_tz import MpesaAPIError  # noqa: E402
from mpesa_tz.contrib.django import services  # noqa: E402
from mpesa_tz.contrib.django.models import Payment  # noqa: E402

from .conftest import B2C_URL, C2B_URL, SESSION_URL, session_ok, success  # noqa: E402

pytestmark = pytest.mark.django_db


def test_migrations_are_up_to_date():
    out = StringIO()
    call_command("makemigrations", "mpesa_tz", "--check", "--dry-run", stdout=out)
    assert "No changes detected" in out.getvalue()


def test_initiate_stk_push_success(client, mocked):
    mocked.add(responses.GET, SESSION_URL, json=session_ok())
    mocked.add(responses.POST, C2B_URL, json=success())
    payment = services.initiate_stk_push("0754123456", 1500, "ORDER1", client=client)

    payment.refresh_from_db()
    assert payment.status == Payment.Status.SUCCESS
    assert payment.phone == "255754123456" and str(payment.amount) == "1500.00"
    assert payment.transaction_id == "TX123" and payment.response_code == "INS-0"
    sent = json.loads(mocked.calls[1].request.body)
    assert sent["input_ThirdPartyConversationID"] == payment.third_party_conversation_id


def test_initiate_stk_push_failure_is_recorded(client, mocked):
    mocked.add(responses.GET, SESSION_URL, json=session_ok())
    mocked.add(responses.POST, C2B_URL, status=400,
               json={"output_ResponseCode": "INS-5", "output_ResponseDesc": "Cancelled by customer"})
    with pytest.raises(MpesaAPIError):
        services.initiate_stk_push("0754123456", 1500, "ORDER1", client=client)
    payment = Payment.objects.get()
    assert payment.status == Payment.Status.FAILED and payment.response_code == "INS-5"


def test_send_b2c(client, mocked):
    mocked.add(responses.GET, SESSION_URL, json=session_ok())
    mocked.add(responses.POST, B2C_URL, json=success())
    payment = services.send_b2c_payment("0754123456", 100, "PAY1", client=client)
    assert payment.kind == Payment.Kind.B2C and payment.status == Payment.Status.SUCCESS


def _pending(tp="TP1"):
    return Payment.objects.create(phone="255754123456", amount=100, reference="R1",
                                  third_party_conversation_id=tp)


def test_callback_view_updates_payment(client_django):
    payment = _pending()
    body = {"input_OriginalConversationID": "CONV9", "input_TransactionID": "TX9",
            "input_ResultCode": "INS-0", "input_ResultDesc": "OK", "input_ThirdPartyConversationID": "TP1"}
    resp = client_django.post("/mpesa/callback/", data=json.dumps(body), content_type="application/json")
    assert resp.status_code == 200
    assert resp.json()["output_ResponseCode"] == "0"
    payment.refresh_from_db()
    assert payment.status == "success" and payment.transaction_id == "TX9" and payment.conversation_id == "CONV9"


def test_callback_view_failed_result(client_django):
    payment = _pending()
    body = {"input_ResultCode": "INS-6", "input_ResultDesc": "Failed", "input_ThirdPartyConversationID": "TP1"}
    client_django.post("/mpesa/callback/", data=json.dumps(body), content_type="application/json")
    payment.refresh_from_db()
    assert payment.status == "failed"


def test_callback_view_unknown_and_invalid(client_django):
    ok = client_django.post("/mpesa/callback/", data=json.dumps({"input_ThirdPartyConversationID": "nope"}),
                            content_type="application/json")
    assert ok.status_code == 200
    bad = client_django.post("/mpesa/callback/", data="not json", content_type="application/json")
    assert bad.status_code == 400
    assert client_django.get("/mpesa/callback/").status_code == 405


def test_get_client_from_settings(settings, monkeypatch, public_key_b64):
    monkeypatch.setenv("MPESA_API_KEY", "k")
    monkeypatch.setenv("MPESA_PUBLIC_KEY", public_key_b64)
    settings.MPESA_TZ = {"SERVICE_PROVIDER_CODE": "777777", "ENVIRONMENT": "production"}
    c = services.get_client()
    assert c.service_provider_code == "777777" and c.environment == "production"


def test_admin_registered():
    from django.contrib import admin

    assert Payment in admin.site._registry
