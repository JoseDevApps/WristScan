from django.shortcuts import render

# Create your views here.
# views.py

from django.shortcuts import render

def qr_scanner_view(request):
    websocket_url = 'ws://localhost/ws/qr/'  # You can dynamically set this URL
    return render(request, 'qr-scan.html', {'websocket_url': websocket_url})