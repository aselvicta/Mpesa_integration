import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ...callbacks import callback_ack, parse_callback
from ...exceptions import MpesaValidationError
from .services import apply_callback

logger = logging.getLogger("mpesa_tz")


@csrf_exempt
@require_POST
def mpesa_callback(request):
    """Receive asynchronous M-Pesa results and update the Payment record."""
    try:
        result = parse_callback(request.body)
    except MpesaValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    payment = apply_callback(result)
    if payment is None:
        logger.warning("M-Pesa callback for unknown transaction: %s", result.raw)
    return JsonResponse(callback_ack(result))
