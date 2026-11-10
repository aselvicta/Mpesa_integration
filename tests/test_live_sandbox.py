"""Live tests against the real M-Pesa OpenAPI sandbox.

Skipped unless MPESA_LIVE_TESTS=1 and MPESA_* credentials are set. See TESTING.md.
"""

import os

import pytest

from mpesa_tz import MpesaClient, generate_reference

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("MPESA_LIVE_TESTS") != "1", reason="set MPESA_LIVE_TESTS=1 to run"),
]


@pytest.fixture(scope="module")
def live_client():
    return MpesaClient.from_env(session_activation_delay=int(os.environ.get("MPESA_SESSION_DELAY", "30")))


def test_live_session(live_client):
    assert live_client.get_session_key()


def test_live_stk_push(live_client):
    phone = os.environ.get("MPESA_TEST_PHONE")
    if not phone:
        pytest.skip("set MPESA_TEST_PHONE")
    result = live_client.stk_push(phone, 100, generate_reference("LIVE"), "mpesa-tz live test")
    assert result.is_success, result.raw
    assert result.transaction_id
