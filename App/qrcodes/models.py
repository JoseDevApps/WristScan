from django.db import models
from django.contrib.auth.models import User
import qrcode
from io import BytesIO
import string
import random
from django.core.files.base import ContentFile
#**********************************************
#   Generacion de codigos Plan 1
#**********************************************
class Event(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    date = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="events")
    qr_codes = models.ManyToManyField("QRCode", blank=True)
    qr_code_count = models.PositiveIntegerField(default=500)
    def generate_qr_codes(self):
        """Genera 500 códigos QR y los asocia al evento."""
        count = self.qr_code_count
        for i in range(count):
            caracteres = string.ascii_letters + string.digits
            qr_data = f"{self.id}-{''.join(random.choice(caracteres) for _ in range(15))}"
            qr = QRCode.objects.create(data=qr_data)
            self.qr_codes.add(qr)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.qr_codes.exists():  # Solo generar QR si no existen
            self.generate_qr_codes()
    def __str__(self) -> str:
        return self.name


class QRCode(models.Model):
    data = models.CharField(max_length=255, unique=True)
    image = models.ImageField(upload_to="qrcodes/", blank=True)

    def save(self, *args, **kwargs):
        """Genera la imagen QR automáticamente al guardar."""
        if not self.image:
            qr = qrcode.make(self.data)
            buffer = BytesIO()
            qr.save(buffer, format="PNG")
            self.image.save(f"{self.data}.png", ContentFile(buffer.getvalue()), save=False)
        super().save(*args, **kwargs)
    def __str__(self) -> str:
        return self.data

class EventRole(models.Model):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("monitor", "Monitor"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    class Meta:
        unique_together = ("user", "event")  # Un usuario no puede tener múltiples roles en el mismo evento
    def __str__(self) -> str:
        return self.user
