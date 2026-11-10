from django.urls import path

from .views import mpesa_callback

app_name = "mpesa_tz"

urlpatterns = [
    path("callback/", mpesa_callback, name="callback"),
]
