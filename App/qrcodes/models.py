from django.db import models
from django.contrib.auth.models import User
import qrcode
from io import BytesIO
import string
import random
import os
from django.conf import settings
import tempfile
from django.core.files.base import ContentFile
from PIL import Image
import io

class Event(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="events")
    qr_codes = models.ManyToManyField("QRCode", blank=True)
    qr_code_count = models.PositiveIntegerField(default=500)
    image = models.ImageField(upload_to="qrmask/", blank=True, null=True)

    def update_qr_codes(self, new_total_qr_count):
        """Updates an event with more QR codes if needed."""
        if not self.image:
            print("❌ Error: No image uploaded for the event.")
            return

        existing_count = self.qr_codes.count()
        if new_total_qr_count > existing_count:
            extra_count = new_total_qr_count - existing_count
            print(f"🔄 Generating {extra_count} additional QR codes...")
            for _ in range(extra_count):
                qr_data = f"{self.id}-{''.join(random.choices(string.ascii_letters + string.digits, k=15))}"
                qr = QRCode(data=qr_data, event_name=self.name)
                qr.process_qr_with_background(self.image)
                qr.save()
                self.qr_codes.add(qr)

            # Update the QR count in the database
            self.qr_code_count = new_total_qr_count
            self.save(update_fields=['qr_code_count'])

        else:
            print("✅ No additional QR codes needed.")

    def generate_qr_codes(self):
        """Genera códigos QR en memoria y los guarda en la base de datos una vez la imagen del evento está cargada."""
        if not self.image:
            print("❌ Error: No se ha cargado una imagen para el evento")
            return

        count = self.qr_code_count
        # Save image in tmp files
        for _ in range(count):
            qr_data = f"{self.id}-{''.join(random.choices(string.ascii_letters + string.digits, k=15))}"
            qr = QRCode(data=qr_data, event_name=self.name)
            qr.process_qr_with_background(self.image)  # Generar QR con la imagen en memoria
            qr.save()  # Guardar en la base de datos
            self.qr_codes.add(qr)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.qr_codes.exists():  # Solo generar QR si no existen
            self.generate_qr_codes()

    def __str__(self):
        return self.name

class QRCode(models.Model):
    STATUS = (
        ('nuevo', 'nuevo'),
        ('concedido', 'concedido'),
        ('duplicado', 'duplicado')
    )
    STATUS_CHOICES = (
        ('available', 'available'),
        ('purchased', 'purchased'),
    )

    data = models.CharField(max_length=255, unique=True)
    image = models.ImageField(upload_to="qrcodes/", blank=True)
    event_name = models.CharField(max_length=255, blank=True)  # Guardamos el nombre del evento
    event_image = models.ImageField(upload_to="qrmask/", blank=True, null=True)  # Guardamos la imagen del evento
    user_email = models.EmailField(max_length=255, blank=True)
    status_scan = models.CharField(max_length=200, default="nuevo", choices=STATUS)
    status_purchased = models.CharField(max_length=200, default="available", choices=STATUS_CHOICES)
    updated_at = models.DateTimeField(auto_now=True)
    def process_qr_with_background(self, event_image):
        """Genera el QR en memoria y lo sobrepone en la imagen del evento."""
        if not self.id:
            super().save()  # Ensure the instance has an ID before proceeding
        # 🔹 1️⃣ Generar QR en memoria
        qr = qrcode.make(self.data)
        qr_buffer = BytesIO()
        qr.save(qr_buffer, format="PNG")

        # 🔹 2️⃣ Procesar la imagen del evento en memoria
        event_image.open()  # 📍 Cargar imagen desde el objeto en memoria
        
         # 🔸 2.1 Si no es 500x500, redimensionar a 720x1280 (como antes)
        if background.size != (500, 500):
            background = Image.open(BytesIO(event_image.file.read())).convert("RGBA")
            background = background.resize((720, 1280))  # Ajustar tamaño
            # Posición del QR en imagen redimensionada (ajustada)
            position = (220, 880)
        else:
            # Si es 500x500, centrar el QR
            position = ((500 - 500) // 2, (500 - 500) // 2)  # (0, 0) o centrado exacto si QR es más pequeño

        # 🔹 3️⃣ Cargar QR en memoria y pegarlo sobre la imagen
        overlay = Image.open(BytesIO(qr_buffer.getvalue())).convert("RGBA")
        # position = (220, 880)  # Posición del QR en la imagen

        background.paste(overlay, position, overlay)

        # 🔹 4️⃣ Guardar imagen final en memoria
        final_buffer = BytesIO()
        background.save(final_buffer, format="PNG")

        # 🔹 5️⃣ Asignar imagen al campo `image` sin escribir en disco
        self.image.save(f"qr_{str(self.id)}_.png", ContentFile(final_buffer.getvalue()), save=False)

    def __str__(self):
        return f"QR {self.id} - {self.data}"

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
