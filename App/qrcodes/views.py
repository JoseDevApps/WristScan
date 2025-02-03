from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

from .models import Event, EventRole, QRCode
from .tasks import send_event_qr_codes


@login_required
def create_event(request):
    if request.method == "POST":
        name = request.POST["name"]
        description = request.POST["description"]
        date = request.POST["date"]
        
        event = Event.objects.create(
            name=name,
            description=description,
            date=date,
            created_by=request.user
        )
        
        # Llamar a la tarea de envío de correo en segundo plano
        send_event_qr_codes.delay(event.id)
        
        return redirect("event_detail", event_id=event.id)

    return render(request, "qrcodes/create_event.html")

def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    event_roles = EventRole.objects.filter(event=event)
    qr_codes = event.qr_codes.all()[:10]  # Show only first 10 QR codes

    return render(request, "qrcodes/event_detail.html", {
        "event": event,
        "event_roles": event_roles,
        "qr_codes": qr_codes,
    })