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
from PIL import ImageDraw, ImageFont
import io
import sys
from django.core.files.uploadedfile import InMemoryUploadedFile

# 💰 Precio dinámico por cantidad
class PriceTier(models.Model):
    min_quantity = models.PositiveIntegerField(null=True, blank=True)
    max_quantity = models.PositiveIntegerField(null=True, blank=True)  # null = sin límite superior
    price_cents = models.PositiveIntegerField(null=True, blank=True,help_text="Price per ticket in cents (e.g. 5 = $0.05)")


    class Meta:
        ordering = ['min_quantity']

    def __str__(self):
        if self.max_quantity:
            return f"{self.min_quantity} - {self.max_quantity} → 0.0{self.price_cents}$"
        return f"{self.min_quantity}+ → ${self.price_cents}"
    def price_in_dollars(self):
        """Returns the price in dollars as Decimal."""
        return self.price_cents / 100

# 🎟️ Ticket comprado por un usuario
class Ticket(models.Model):
    user_name = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ticket")
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user_name} ({self.quantity} tickets)"

    def get_price_tier(self):
        tiers = PriceTier.objects.order_by('min_quantity')
        for tier in tiers:
            if tier.max_quantity is None or self.quantity <= tier.max_quantity:
                if self.quantity >= tier.min_quantity:
                    return tier
        return None

    def price_per_ticket(self):
        tier = self.get_price_tier()
        return tier.price_cents if tier else 0.05

    def total_amount(self):
        return round(self.quantity * self.price_per_ticket(), 2)

    def assigned_quantity(self):
        return sum(a.quantity for a in self.assignments.all())

    def unassigned_quantity(self):
        return self.quantity - self.assigned_quantity()


# 💳 Pago del ticket
class Payment(models.Model):
    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    paid_at = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50)

    def save(self, *args, **kwargs):
        if not self.amount:
            self.amount = self.ticket.total_amount()
        self.ticket.is_paid = True
        self.ticket.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payment for {self.ticket}"



class Event(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="events")
    qr_codes = models.ManyToManyField("QRCode", blank=True)
    qr_code_count = models.PositiveIntegerField(default=1)
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
        overlay = Image.open(BytesIO(qr_buffer.getvalue())).convert("RGBA")
        # 🔹 2️⃣ Procesar la imagen del evento en memoria
        event_image.open()  # 📍 Cargar imagen desde el objeto en memoria
        background = Image.open(BytesIO(event_image.file.read())).convert("RGBA")
        width, height = overlay.size
        # background = background.resize((720, 1280))  # Ajustar tamaño
        if background.size != (400, 400):
            background = background.resize((720, 1280))

            # Posición del QR en imagen redimensionada (ajustada)
            position = (220, 880)
        else:
            # Si es 500x500, centrar el QR
            # Calcula el offset para centrar:
            
            offset_x = (400 - width) // 2
            offset_y = (400 - height) // 2
            position = (offset_x, offset_y)
            # position = (135, 135)  # (0, 0) o centrado exacto si QR es más pequeño


        # 🔹 3️⃣ Cargar QR en memoria y pegarlo sobre la imagen
        

        background.paste(overlay, position, overlay)

        # 4️⃣ Dibujar texto con el ID del QR
        draw = ImageDraw.Draw(background)
        rect_width, rect_height = 400, 50
        # Calcula coordenadas del rectángulo: parte inferior de la imagen
        rect_x0 = 0
        rect_y0 = background.height - 50
        rect_x1 = 400
        rect_y1 = background.height

        draw.rectangle([rect_x0, rect_y0, rect_x1, rect_y1], fill="black")

        # Intentar cargar una fuente TTF (o usar por defecto)
        try:
            font = ImageFont.truetype("arial.ttf", 25)  # asegúrate que arial.ttf esté disponible en tu entorno
        except:
            font = ImageFont.load_default(size=25)
        

        text = f"ID: {self.id}"
        text_position = (position[0]+(width//2)-30, position[1] + overlay.size[1] -15)  # Debajo del QR
        text_color = (255, 255, 255)  # Blanco

        text_width, text_height = draw.textsize(text, font=font)
        # Calcula la posición para centrar el texto horizontal y verticalmente
        text_x = rect_x0 + (rect_width - text_width) // 2
        text_y = rect_y0 + (rect_height - text_height) // 2

        draw.text((text_x, text_y), text, fill=text_color, font=font)

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

# 🔗 Relación de tickets distribuidos entre eventos
class TicketAssignment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="assignments")
    event = models.CharField(max_length=255, blank=True)
    quantity = models.PositiveIntegerField()
    event_fk = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="ticket_assignments", null=True, blank=True)

    def assign_qr_codes(self):
        # 🔹 Crear evento
        image_save = Image.new('RGB', (400, 400), color='white')
        buffer = io.BytesIO()
        image_save.save(buffer, format="jpeg")
        buffer.seek(0)
        temp_image_file = InMemoryUploadedFile(
            buffer, None, "temp_image.png", "image/png", sys.getsizeof(buffer), None
        )
        self.event_fk = Event.objects.create(
            name=self.event,
            created_by=self.ticket.user_name,
            qr_code_count=self.quantity,
            image=temp_image_file
        )
    def save(self, *args, **kwargs):
        self.assign_qr_codes()
        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.quantity} tickets of {self.ticket} assigned to {self.event or 'New Event'}"
    