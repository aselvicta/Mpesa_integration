"""M-Pesa Tanzania (Vodacom M-Pesa OpenAPI) client."""

import logging
import os
import threading
import time

import requests

from . import config
from .codes import AUTH_ERROR_CODES, SUCCESS_CODE, describe
from .crypto import encrypt, load_public_key
from .exceptions import (
    MpesaAPIError,
    MpesaAuthError,
    MpesaConfigError,
    MpesaConnectionError,
    MpesaValidationError,
)
from .models import MpesaResponse
from .stk import STKPush
from .utils import (
    format_amount,
    generate_conversation_id,
    normalize_phone,
    validate_reference,
)

logger = logging.getLogger("mpesa_tz")


class MpesaClient:
    """Client for the Vodacom Tanzania M-Pesa OpenAPI.

    Example::

        client = MpesaClient(
            api_key="...",
            public_key="MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEA...",
            service_provider_code="000000",
            environment="sandbox",
        )
        result = client.stk_push("0754123456", 1000, "ORDER1")
        print(result.transaction_id)

    Args:
        api_key: API key from the M-Pesa OpenAPI developer portal.
        public_key: Public key from the portal (base64 DER or PEM).
        service_provider_code: Your business shortcode.
        environment: ``"sandbox"`` (default) or ``"production"``.
        base_url: Override the API base URL (takes precedence over environment).
        country / currency: Defaults ``"TZN"`` / ``"TZS"``.
        origin: Value for the ``Origin`` header (must match the portal setting).
        timeout: HTTP timeout in seconds.
        session_ttl: Seconds to reuse a session key before requesting a new one.
        session_activation_delay: Seconds to wait after creating a new session.
            The sandbox can take a few seconds to activate a new session key.
        strict_phone: Only accept valid Tanzanian mobile numbers. Defaults to
            ``True`` except in the sandbox, whose test MSISDNs (e.g.
            ``000000000001``) are not real numbers.
        raise_on_error: If ``False``, API errors are returned as an
            unsuccessful :class:`MpesaResponse` instead of raising.
        http_session: Optional ``requests.Session`` (useful for retries/tests).
    """

    def __init__(
        self,
        api_key=None,
        public_key=None,
        service_provider_code=None,
        environment=config.SANDBOX,
        base_url=None,
        country=config.DEFAULT_COUNTRY,
        currency=config.DEFAULT_CURRENCY,
        origin="*",
        timeout=config.DEFAULT_TIMEOUT,
        session_ttl=config.DEFAULT_SESSION_TTL,
        session_activation_delay=0,
        raise_on_error=True,
        strict_phone=None,
        http_session=None,
    ):
        if not api_key:
            raise MpesaConfigError("api_key is required")
        if not public_key:
            raise MpesaConfigError("public_key is required")
        environment = (environment or config.SANDBOX).lower()
        if base_url is None:
            if environment not in config.BASE_URLS:
                raise MpesaConfigError(
                    "environment must be one of %s, got %r"
                    % (sorted(config.BASE_URLS), environment)
                )
            base_url = config.BASE_URLS[environment]

        self.api_key = api_key
        self.public_key = load_public_key(public_key)
        self.service_provider_code = service_provider_code
        self.environment = environment
        self.base_url = base_url.rstrip("/")
        self.country = country
        self.currency = currency
        self.origin = origin
        self.timeout = timeout
        self.session_ttl = session_ttl
        self.session_activation_delay = session_activation_delay
        self.raise_on_error = raise_on_error
        self.strict_phone = (environment != config.SANDBOX) if strict_phone is None else strict_phone
        self.http = http_session or requests.Session()

        self._session_id = None
        self._session_expires_at = 0.0
        self._lock = threading.Lock()

        # Backwards compatible 0.1.x API: client.stk.push(phone, amount, reference)
        self.stk = STKPush(self)

    # ------------------------------------------------------------------ setup
    @classmethod
    def from_env(cls, prefix="MPESA_", load_dotenv=True, **overrides):
        """Build a client from environment variables.

        Reads ``MPESA_API_KEY``, ``MPESA_PUBLIC_KEY``,
        ``MPESA_SERVICE_PROVIDER_CODE``, ``MPESA_ENVIRONMENT``,
        ``MPESA_BASE_URL``, ``MPESA_ORIGIN`` and ``MPESA_TIMEOUT``.
        A ``.env`` file is loaded first if ``python-dotenv`` is installed.
        """
        if load_dotenv:
            try:
                from dotenv import load_dotenv as _load

                _load()
            except ImportError:
                pass

        def env(name, default=None):
            return os.environ.get(prefix + name, default)

        kwargs = {
            "api_key": env("API_KEY"),
            "public_key": env("PUBLIC_KEY"),
            "service_provider_code": env("SERVICE_PROVIDER_CODE"),
            "environment": env("ENVIRONMENT", config.SANDBOX),
            "base_url": env("BASE_URL"),
            "origin": env("ORIGIN", "*"),
        }
        if env("TIMEOUT"):
            kwargs["timeout"] = float(env("TIMEOUT"))
        kwargs.update(overrides)
        return cls(**kwargs)

    # ---------------------------------------------------------------- session
    def get_session_key(self, force_refresh=False):
        """Return a valid session id, creating (and caching) one if needed."""
        with self._lock:
            if not force_refresh and self._session_id and time.time() < self._session_expires_at:
                return self._session_id

            headers = {
                "Authorization": "Bearer " + encrypt(self.api_key, self.public_key),
                "Origin": self.origin,
                "Content-Type": "application/json",
            }
            payload, status = self._send("GET", config.ENDPOINTS["session"], headers=headers)
            code = payload.get("output_ResponseCode")
            session_id = payload.get("output_SessionID")
            if code != SUCCESS_CODE or not session_id:
                desc = payload.get("output_ResponseDesc") or describe(code)
                raise MpesaAuthError(
                    "Could not obtain session key: %s (%s)" % (desc, code),
                    code=code,
                    description=desc,
                    status_code=status,
                    response=payload,
                )

            self._session_id = session_id
            self._session_expires_at = time.time() + self.session_ttl
            logger.debug("Obtained new M-Pesa session key")
            if self.session_activation_delay:
                time.sleep(self.session_activation_delay)
            return session_id

    def invalidate_session(self):
        """Forget the cached session key; the next call creates a new one."""
        with self._lock:
            self._session_id = None
            self._session_expires_at = 0.0

    # ---------------------------------------------------------------- helpers
    def _require_shortcode(self):
        if not self.service_provider_code:
            raise MpesaConfigError("service_provider_code is required for this operation")
        return self.service_provider_code

    def _send(self, method, endpoint, headers, json=None, params=None):
        url = self.base_url + endpoint
        try:
            resp = self.http.request(
                method, url, headers=headers, json=json, params=params, timeout=self.timeout
            )
        except requests.Timeout as exc:
            raise MpesaConnectionError("Request to M-Pesa timed out: %s" % exc) from exc
        except requests.RequestException as exc:
            raise MpesaConnectionError("Could not reach M-Pesa: %s" % exc) from exc

        try:
            payload = resp.json()
            if not isinstance(payload, dict):
                raise ValueError("not an object")
        except ValueError:
            raise MpesaAPIError(
                "Unexpected non-JSON response from M-Pesa (HTTP %s): %s"
                % (resp.status_code, resp.text[:200]),
                status_code=resp.status_code,
            )
        return payload, resp.status_code

    def _request(self, method, endpoint, json=None, params=None, _retry=True):
        session_id = self.get_session_key()
        headers = {
            "Authorization": "Bearer " + encrypt(session_id, self.public_key),
            "Origin": self.origin,
            "Content-Type": "application/json",
        }
        payload, status = self._send(method, endpoint, headers=headers, json=json, params=params)
        result = MpesaResponse.from_payload(payload, status_code=status)

        if result.is_success:
            return result

        # Session expired / revoked: get a fresh one and retry once.
        if _retry and (result.code in AUTH_ERROR_CODES or status == 401):
            logger.info("M-Pesa rejected session (%s); refreshing and retrying", result.code)
            self.invalidate_session()
            return self._request(method, endpoint, json=json, params=params, _retry=False)

        if not self.raise_on_error:
            return result

        desc = result.description or describe(result.code)
        error_cls = MpesaAuthError if result.code in AUTH_ERROR_CODES else MpesaAPIError
        raise error_cls(
            "M-Pesa request failed: %s (%s)" % (desc, result.code),
            code=result.code,
            description=desc,
            status_code=status,
            response=payload,
        )

    # ------------------------------------------------------------- operations
    def c2b_payment(self, phone, amount, reference, description="Payment", conversation_id=None):
        """Customer-to-business payment: prompts the customer to enter their PIN.

        This is the "STK push" flow. The call blocks until the customer
        confirms/declines or the request times out.
        """
        body = {
            "input_Amount": format_amount(amount),
            "input_Country": self.country,
            "input_Currency": self.currency,
            "input_CustomerMSISDN": normalize_phone(phone, strict=self.strict_phone),
            "input_ServiceProviderCode": self._require_shortcode(),
            "input_ThirdPartyConversationID": conversation_id or generate_conversation_id(),
            "input_TransactionReference": validate_reference(reference),
            "input_PurchasedItemsDesc": str(description)[:256],
        }
        return self._request("POST", config.ENDPOINTS["c2b"], json=body)

    #: Alias - most developers know the C2B prompt as "STK push".
    stk_push = c2b_payment

    def b2c_payment(self, phone, amount, reference, description="Payment", conversation_id=None):
        """Business-to-customer payment (send money to a customer)."""
        body = {
            "input_Amount": format_amount(amount),
            "input_Country": self.country,
            "input_Currency": self.currency,
            "input_CustomerMSISDN": normalize_phone(phone, strict=self.strict_phone),
            "input_ServiceProviderCode": self._require_shortcode(),
            "input_ThirdPartyConversationID": conversation_id or generate_conversation_id(),
            "input_TransactionReference": validate_reference(reference),
            "input_PaymentItemsDesc": str(description)[:256],
        }
        return self._request("POST", config.ENDPOINTS["b2c"], json=body)

    def b2b_payment(self, receiver_party_code, amount, reference, description="Payment", conversation_id=None):
        """Business-to-business payment to another shortcode."""
        if not receiver_party_code:
            raise MpesaValidationError("receiver_party_code is required")
        body = {
            "input_Amount": format_amount(amount),
            "input_Country": self.country,
            "input_Currency": self.currency,
            "input_PrimaryPartyCode": self._require_shortcode(),
            "input_ReceiverPartyCode": str(receiver_party_code),
            "input_ThirdPartyConversationID": conversation_id or generate_conversation_id(),
            "input_TransactionReference": validate_reference(reference),
            "input_PurchasedItemsDesc": str(description)[:256],
        }
        return self._request("POST", config.ENDPOINTS["b2b"], json=body)

    def query_transaction_status(self, query_reference, conversation_id=None):
        """Look up a transaction by transaction id, conversation id or reference."""
        if not query_reference:
            raise MpesaValidationError("query_reference is required")
        params = {
            "input_QueryReference": str(query_reference),
            "input_ServiceProviderCode": self._require_shortcode(),
            "input_ThirdPartyConversationID": conversation_id or generate_conversation_id(),
            "input_Country": self.country,
        }
        return self._request("GET", config.ENDPOINTS["query"], params=params)

    def reversal(self, transaction_id, amount, conversation_id=None):
        """Reverse a successful transaction (full or partial amount)."""
        if not transaction_id:
            raise MpesaValidationError("transaction_id is required")
        body = {
            "input_ReversalAmount": format_amount(amount),
            "input_Country": self.country,
            "input_ServiceProviderCode": self._require_shortcode(),
            "input_ThirdPartyConversationID": conversation_id or generate_conversation_id(),
            "input_TransactionID": str(transaction_id),
        }
        return self._request("PUT", config.ENDPOINTS["reversal"], json=body)

    def __repr__(self):
        return "<MpesaClient environment=%r base_url=%r shortcode=%r>" % (
            self.environment,
            self.base_url,
            self.service_provider_code,
        )
