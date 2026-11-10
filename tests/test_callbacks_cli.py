import json

import pytest
import responses

import mpesa_tz
from mpesa_tz import MpesaValidationError, callback_ack, parse_callback
from mpesa_tz.__main__ import main

from .conftest import C2B_URL, SESSION_URL, session_ok, success

CALLBACK = {
    "input_OriginalConversationID": "CONV1",
    "input_TransactionID": "TX1",
    "input_ResultCode": "INS-0",
    "input_ResultDesc": "Request processed successfully",
    "input_ThirdPartyConversationID": "TP1",
}


@pytest.mark.parametrize("body", [CALLBACK, json.dumps(CALLBACK), json.dumps(CALLBACK).encode()])
def test_parse_callback(body):
    r = parse_callback(body)
    assert r.is_success and r.transaction_id == "TX1"
    assert r.conversation_id == "CONV1" and r.third_party_conversation_id == "TP1"


def test_parse_failed_callback():
    r = parse_callback(dict(CALLBACK, input_ResultCode="INS-5"))
    assert not r.is_success


@pytest.mark.parametrize("bad", ["not json", b"[1,2]", 42])
def test_parse_callback_invalid(bad):
    with pytest.raises(MpesaValidationError):
        parse_callback(bad)


def test_callback_ack():
    ack = callback_ack(parse_callback(CALLBACK))
    assert ack == {
        "output_OriginalConversationID": "CONV1",
        "output_ResponseCode": "0",
        "output_ResponseDesc": "Successfully Accepted Result",
        "output_ThirdPartyConversationID": "TP1",
    }
    assert callback_ack(parse_callback(CALLBACK), accepted=False)["output_ResponseCode"] == "1"


def test_public_api_exports():
    for name in mpesa_tz.__all__:
        assert hasattr(mpesa_tz, name), name
    assert mpesa_tz.__version__ == "0.2.0"


def test_cli_session(client, mocked, capsys):
    mocked.add(responses.GET, SESSION_URL, json=session_ok())
    assert main(["session"], client=client) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_cli_stk_push(client, mocked, capsys):
    mocked.add(responses.GET, SESSION_URL, json=session_ok())
    mocked.add(responses.POST, C2B_URL, json=success())
    assert main(["stk-push", "--phone", "0754123456", "--amount", "100", "--reference", "R1"], client=client) == 0
    assert json.loads(capsys.readouterr().out)["transaction_id"] == "TX123"


def test_cli_error_exit_code(client, mocked, capsys):
    mocked.add(responses.GET, SESSION_URL, status=401, json={"output_ResponseCode": "INS-2"})
    assert main(["session"], client=client) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False and out["code"] == "INS-2"


def test_cli_missing_config(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)  # make sure no real .env is picked up
    monkeypatch.delenv("MPESA_API_KEY", raising=False)
    monkeypatch.delenv("MPESA_PUBLIC_KEY", raising=False)
    assert main(["session"]) == 1
    assert "MpesaConfigError" in capsys.readouterr().out
