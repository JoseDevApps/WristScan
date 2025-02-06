# myapp/routing.py

from django.urls import path
from qrscan.consumers import QRConsumer

websocket_urlpatterns = [
    path('ws/qr/', QRConsumer.as_asgi()),  # WebSocket URL for QR scanning
]