from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from zipfile import ZipFile
import os
from django.utils import timezone
from dashboard.models import  AdPlacement, AdDefaults
from .models import QRCode
@shared_task
def send_event_qr_codes(event_id):
    from .models import Event

    event = Event.objects.get(id=event_id)
    print(event.created_by.email)
    creator_email = event.created_by.email

    zip_filename = f"{event.name}_qr_codes.zip"
    zip_path = os.path.join(settings.MEDIA_ROOT, zip_filename)

    with ZipFile(zip_path, "w") as zip_file:
        for qr in event.qr_codes.all():
            zip_file.write(qr.image.path, os.path.basename(qr.image.path))

    email = EmailMessage(
        subject=f"QR Codes for {event.name}",
        body=f"Attached are {event.qr_code_count} QR codes for your event.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[creator_email],
    )
    print(zip_filename)
    print(zip_path)
    print(creator_email)
    print(settings.DEFAULT_FROM_EMAIL)
    email.attach_file("/codigo/media/"+zip_filename)
    email.send()

# --- NUEVA tarea para limpiar QR gratuitos expirados ---
@shared_task
def cleanup_free_qrs_task():
    """
    Elimina QR gratuitos cuya ad placement haya expirado
    o cuya fecha de AdDefaults haya expirado si no hay país asignado.
    """
    now = timezone.now()
    deleted_count = 0

    # QR gratuitos
    free_qrs = QRCode.objects.filter(enable_top_banner=True, ticket__plan='free')

    for qr in free_qrs:
        ad = None
        # buscar AdPlacement asociado al país del QR (si lo tiene)
        country = getattr(qr, "country_code", None)
        if country:
            try:
                ad = AdPlacement.objects.filter(country=country, active=True).first()
            except AdPlacement.DoesNotExist:
                ad = None
        else:
            # fallback a AdDefaults
            ad = AdDefaults.get_solo()

        if ad:
            # revisar fechas
            starts_at = getattr(ad, "starts_at", None)
            ends_at = getattr(ad, "ends_at", None)
            if (starts_at and now < starts_at) or (ends_at and now > ends_at):
                # eliminar QR
                qr.delete()
                deleted_count += 1

    return deleted_count