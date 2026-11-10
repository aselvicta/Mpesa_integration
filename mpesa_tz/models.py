"""Plain data objects returned by the client (no framework dependency)."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .codes import SUCCESS_CODE, describe


@dataclass
class MpesaResponse:
    """Normalised view of an M-Pesa OpenAPI response."""

    code: Optional[str]
    description: Optional[str]
    conversation_id: Optional[str] = None
    third_party_conversation_id: Optional[str] = None
    transaction_id: Optional[str] = None
    status_code: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self):
        return self.code == SUCCESS_CODE

    @property
    def code_description(self):
        return describe(self.code)

    def get(self, key, default=None):
        """Dict-style access to the raw payload (backwards compatible with 0.1)."""
        return self.raw.get(key, default)

    def __getitem__(self, key):
        return self.raw[key]

    def to_dict(self):
        return {
            "code": self.code,
            "description": self.description,
            "conversation_id": self.conversation_id,
            "third_party_conversation_id": self.third_party_conversation_id,
            "transaction_id": self.transaction_id,
            "is_success": self.is_success,
            "raw": self.raw,
        }

    @classmethod
    def from_payload(cls, payload, status_code=None):
        payload = payload or {}
        return cls(
            code=payload.get("output_ResponseCode"),
            description=payload.get("output_ResponseDesc"),
            conversation_id=payload.get("output_ConversationID"),
            third_party_conversation_id=payload.get("output_ThirdPartyConversationID"),
            transaction_id=payload.get("output_TransactionID"),
            status_code=status_code,
            raw=dict(payload),
        )
