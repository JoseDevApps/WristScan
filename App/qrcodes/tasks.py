from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from zipfile import ZipFile
import os

@shared_task
def send_event_qr_codes(event_id):
    from .models import Event

    event = Event.objects.get(id=event_id)
    creator_email = event.created_by.email

    zip_filename = f"{event.name}_qr_codes.zip"
    zip_path = os.path.join(settings.MEDIA_ROOT, zip_filename)

    with ZipFile(zip_path, "w") as zip_file:
        for qr in event.qr_codes.all():
            zip_file.write(qr.image.path, os.path.basename(qr.image.path))

    email = EmailMessage(
        subject=f"QR Codes for {event.name}",
        body="Attached are the 500 QR codes for your event.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[creator_email],
    )
    print(zip_filename)
    print(zip_path)
    print(creator_email)
    print(settings.DEFAULT_FROM_EMAIL)
    email.attach_file("/codigo/media/"+zip_filename)
    email.send()
