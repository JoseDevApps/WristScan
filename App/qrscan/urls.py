from django.urls import path
from dashboard.views import qrscan

urlpatterns = [
    path('', qrscan, name='qr_scanner'),  # This serves the HTML page
]