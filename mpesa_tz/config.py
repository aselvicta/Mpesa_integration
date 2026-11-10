"""Environment / endpoint configuration."""

SANDBOX = "sandbox"
PRODUCTION = "production"

BASE_URLS = {
    SANDBOX: "https://openapi.m-pesa.com/sandbox/ipg/v2/vodacomTZN",
    PRODUCTION: "https://openapi.m-pesa.com/openapi/ipg/v2/vodacomTZN",
}

DEFAULT_COUNTRY = "TZN"
DEFAULT_CURRENCY = "TZS"
DEFAULT_TIMEOUT = 60  # C2B single stage waits for the customer to enter a PIN
DEFAULT_SESSION_TTL = 50 * 60  # refresh session keys a bit before they expire

ENDPOINTS = {
    "session": "/getSession/",
    "c2b": "/c2bPayment/singleStage/",
    "b2c": "/b2cPayment/singleStage/",
    "b2b": "/b2bPayment/singleStage/",
    "query": "/queryTransactionStatus/",
    "reversal": "/reversal/",
}

