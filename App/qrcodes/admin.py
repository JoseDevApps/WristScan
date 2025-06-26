from django.contrib import admin
from .models import Event, QRCode, EventRole, PriceTier, Ticket, Payment, TicketAssignment

admin.site.register(PriceTier)
admin.site.register(Ticket)
admin.site.register(Payment)
admin.site.register(Event)
admin.site.register(QRCode)
admin.site.register(EventRole)
admin.site.register(TicketAssignment)