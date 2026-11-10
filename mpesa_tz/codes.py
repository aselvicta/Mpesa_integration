"""M-Pesa OpenAPI response codes (Vodacom Tanzania / M-Pesa OpenAPI)."""

SUCCESS_CODE = "INS-0"

RESPONSE_CODES = {
    "INS-0": "Request processed successfully",
    "INS-1": "Internal error",
    "INS-2": "Invalid API key",
    "INS-4": "User is not active",
    "INS-5": "Transaction cancelled by customer",
    "INS-6": "Transaction failed",
    "INS-9": "Request timeout",
    "INS-10": "Duplicate transaction",
    "INS-13": "Invalid shortcode used",
    "INS-14": "Invalid reference used",
    "INS-15": "Invalid amount used",
    "INS-16": "Unable to handle the request due to a temporary overloading",
    "INS-17": "Invalid transaction reference. Length must be between 1 and 20",
    "INS-18": "Invalid TransactionID used",
    "INS-19": "Invalid ThirdPartyID used",
    "INS-20": "Not all parameters provided. Please try again",
    "INS-21": "Parameter validations failed. Please try again",
    "INS-22": "Invalid operation type",
    "INS-23": "Unknown status. Contact M-Pesa support",
    "INS-24": "Invalid InitiatorIdentifier used",
    "INS-25": "Invalid SecurityCredential used",
    "INS-26": "Not authorized",
    "INS-993": "Direct debit missing",
    "INS-994": "Direct debit already exists",
    "INS-995": "Customer's profile has problems",
    "INS-996": "Customer account status not active",
    "INS-997": "Linking transaction not found",
    "INS-998": "Invalid market",
    "INS-2001": "Initiator authentication error",
    "INS-2002": "Receiver invalid",
    "INS-2006": "Insufficient balance",
    "INS-2051": "MSISDN invalid",
    "INS-2057": "Language code invalid",
}

#: Codes that mean the credentials/session are the problem.
AUTH_ERROR_CODES = {"INS-2", "INS-26"}


def describe(code):
    """Return a human readable description for an ``INS-*`` code."""
    return RESPONSE_CODES.get(code, "Unknown response code")
