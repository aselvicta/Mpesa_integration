from django.urls import include, path

urlpatterns = [path("mpesa/", include("mpesa_tz.contrib.django.urls"))]
