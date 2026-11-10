"""Exception hierarchy for mpesa_tz.

Every exception raised by this package inherits from :class:`MpesaError`,
so callers can catch a single type if they don't care about the details.
"""


class MpesaError(Exception):
    """Base class for all mpesa_tz errors."""


class MpesaConfigError(MpesaError):
    """Missing or invalid client configuration (API key, public key, ...)."""


class MpesaValidationError(MpesaError, ValueError):
    """A request argument (phone, amount, reference, ...) is invalid."""


class MpesaConnectionError(MpesaError):
    """The M-Pesa API could not be reached (DNS, timeout, TLS, ...)."""


class MpesaAPIError(MpesaError):
    """The M-Pesa API answered, but with an error.

    Attributes:
        code: The M-Pesa response code, e.g. ``"INS-2006"`` (may be ``None``).
        description: Human readable description returned by the API.
        status_code: HTTP status code of the response.
        response: The decoded JSON body (or ``{}`` if it was not JSON).
    """

    def __init__(self, message, code=None, description=None, status_code=None, response=None):
        super().__init__(message)
        self.code = code
        self.description = description
        self.status_code = status_code
        self.response = response or {}


class MpesaAuthError(MpesaAPIError):
    """Authentication failed (invalid API key, session expired, ...)."""
