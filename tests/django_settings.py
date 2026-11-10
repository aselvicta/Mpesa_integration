SECRET_KEY = "tests"
DEBUG = True
USE_TZ = True
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "mpesa_tz.contrib.django",
]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
ROOT_URLCONF = "tests.django_urls"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
MPESA_TZ = {"SERVICE_PROVIDER_CODE": "000000"}
