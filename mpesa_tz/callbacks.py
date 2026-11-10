"""Helpers for asynchronous result callbacks.

Synchronous calls (the default for C2B single stage) return the final result
directly. If your M-Pesa account is configured to deliver results
asynchronously to a callback URL, M-Pesa POSTs a JSON body with ``input_*``
fields and expects an acknowledgement with ``output_*`` fields. These helpers
are framework agnostic - use them from Django, Flask, FastAPI, etc.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .codes import SUCCESS_CODE
from .exceptions import MpesaValidationError

_SUCCESS_RESULT_CODES = {SUCCESS_CODE, "0"}


@dataclass
class CallbackResult:
    result_code: Optional[str]
    result_description: Optional[str]
    transaction_id: Optional[str] = None
    conversation_id: Optional[str] = None
    third_party_conversation_id: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self):
        return self.result_code in _SUCCESS_RESULT_CODES


def parse_callback(body):
    """Parse a callback body (``dict``, JSON ``str`` or ``bytes``)."""
    if isinstance(body, (bytes, bytearray)):
        body = body.decode("utf-8")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except ValueError as exc:
            raise MpesaValidationError("Callback body is not valid JSON") from exc
    if not isinstance(body, dict):
        raise MpesaValidationError("Callback body must be a JSON object")

    def pick(*names):
        for name in names:
            if body.get(name) not in (None, ""):
                return str(body[name])
        return None

    return CallbackResult(
        result_code=pick("input_ResultCode", "output_ResponseCode"),
        result_description=pick("input_ResultDesc", "output_ResponseDesc"),
        transaction_id=pick("input_TransactionID", "output_TransactionID"),
        conversation_id=pick("input_OriginalConversationID", "input_ConversationID", "output_ConversationID"),
        third_party_conversation_id=pick("input_ThirdPartyConversationID", "output_ThirdPartyConversationID"),
        raw=dict(body),
    )


def callback_ack(result, accepted=True):
    """Build the acknowledgement body M-Pesa expects in reply to a callback."""
    return {
        "output_OriginalConversationID": result.conversation_id,
        "output_ResponseCode": "0" if accepted else "1",
        "output_ResponseDesc": "Successfully Accepted Result" if accepted else "Rejected",
        "output_ThirdPartyConversationID": result.third_party_conversation_id,
    }
