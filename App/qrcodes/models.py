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

#**********************************************
#   Generacion de codigos Plan 1
#**********************************************
# class Event(models.Model):
#     name = models.CharField(max_length=255)
#     description = models.TextField()
#     date = models.DateTimeField()
#     created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="events")
#     qr_codes = models.ManyToManyField("QRCode", blank=True)
#     qr_code_count = models.PositiveIntegerField(default=500)
#     image = models.ImageField(upload_to="qrmask/", blank=True)
#     def generate_qr_codes(self):
#         """Genera 500 códigos QR y los asocia al evento."""
#         count = self.qr_code_count
#         for i in range(count):
#             caracteres = string.ascii_letters + string.digits
#             qr_data = f"{self.id}-{''.join(random.choice(caracteres) for _ in range(15))}"
#             qr = QRCode.objects.create(data=qr_data,event_name = self.name, event_image = self.image )
#             self.qr_codes.add(qr)

#     def save(self, *args, **kwargs):
#         super().save(*args, **kwargs)
#         if not self.qr_codes.exists():  # Solo generar QR si no existen
#             self.generate_qr_codes()
#     def __str__(self) -> str:
#         return self.name

class Event(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="events")
    qr_codes = models.ManyToManyField("QRCode", blank=True)
    qr_code_count = models.PositiveIntegerField(default=500)
    image = models.ImageField(upload_to="qrmask/", blank=True, null=True)

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
    data = models.CharField(max_length=255, unique=True)
    image = models.ImageField(upload_to="qrcodes/", blank=True)
    event_name = models.CharField(max_length=255, blank=True)  # Guardamos el nombre del evento
    event_image = models.ImageField(upload_to="qrmask/", blank=True, null=True)  # Guardamos la imagen del evento
    user_email = models.EmailField(max_length=255, blank=True)
    def process_qr_with_background(self, event_image):
        """Genera el QR en memoria y lo sobrepone en la imagen del evento."""
        # 🔹 1️⃣ Generar QR en memoria
        qr = qrcode.make(self.data)
        qr_buffer = BytesIO()
        qr.save(qr_buffer, format="PNG")

        # 🔹 2️⃣ Procesar la imagen del evento en memoria
        event_image.open()  # 📍 Cargar imagen desde el objeto en memoria
        background = Image.open(BytesIO(event_image.file.read())).convert("RGBA")
        background = background.resize((720, 1280))  # Ajustar tamaño

        # 🔹 3️⃣ Cargar QR en memoria y pegarlo sobre la imagen
        overlay = Image.open(BytesIO(qr_buffer.getvalue())).convert("RGBA")
        position = (220, 880)  # Posición del QR en la imagen

        background.paste(overlay, position, overlay)

        # 🔹 4️⃣ Guardar imagen final en memoria
        final_buffer = BytesIO()
        background.save(final_buffer, format="PNG")

        # 🔹 5️⃣ Asignar imagen al campo `image` sin escribir en disco
        self.image.save(f"{self.data}_final.png", ContentFile(final_buffer.getvalue()), save=False)

    def __str__(self):
        return self.data
    # def save(self, *args, **kwargs):
    #     """Genera la imagen QR automáticamente al guardar."""
    #     if not self.image:
    #         qr = qrcode.make(self.data)
    #         buffer = BytesIO()
    #         qr.save(buffer, format="PNG")
    #         qr_image = ContentFile(buffer.getvalue())
    #         self.image.save(f"{self.data}.png", ContentFile(buffer.getvalue()), save=False)
    #         # Agregar mascara con fondo y id, y nombre del evento
    #         # Si hay una imagen de evento, combinamos con el QR
    #         print(self.event_image)
    #         if self.event_image:
    #             try:
    #                 print('existe imagen')
    #                 print(self.event_image)
    #                 self.event_image.open()
    #                 event_image_data = BytesIO(self.event_image.file.read())
    #                 print(event_image_data)
    #                 background = Image.open(event_image_data).convert("RGBA")
    #                 background = background.resize((720, 1280))  # Ajustar tamaño
    #                 overlay = Image.open(qr_image).convert("RGBA")
                    
    #                 position = (220, 880)  # Posición del QR en la imagen de fondo
    #                 background.paste(overlay, position, overlay)

    #                 final_buffer = BytesIO()
    #                 background.save(final_buffer, format="PNG")
    #                 self.image.save(f"{self.data}_final.png", ContentFile(final_buffer.getvalue()), save=False)
    #                 self.event_image.close()
    #             except Exception as e:
    #                 print(f"Error al procesar la imagen del evento: {e}")

    #         ###
    #     super().save(*args, **kwargs)
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
