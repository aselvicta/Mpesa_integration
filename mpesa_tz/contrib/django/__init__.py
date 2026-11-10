"""Optional Django integration.

Add ``"mpesa_tz.contrib.django"`` to ``INSTALLED_APPS`` and run ``migrate``.
Settings (all optional if the matching MPESA_* environment variables are set)::

    MPESA_TZ = {
        "API_KEY": "...",
        "PUBLIC_KEY": "...",
        "SERVICE_PROVIDER_CODE": "000000",
        "ENVIRONMENT": "sandbox",
    }
"""

default_app_config = "mpesa_tz.contrib.django.apps.MpesaTzConfig"
