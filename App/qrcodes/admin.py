from django.contrib import admin
from .models import Event, QRCode, EventRole

admin.site.register(Event)
admin.site.register(QRCode)
admin.site.register(EventRole)
