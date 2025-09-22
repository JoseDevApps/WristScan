from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from PIL import Image

class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.IntegerField(default=0)  # cents
    file = models.FileField(upload_to="product_files/", blank=True, null=True)
    url = models.URLField()

    def __str__(self):
        return self.name
    
    def get_display_price(self):
        return "{0:.0f}".format(self.price / 100)
    

TOP_BANNER_RECOMMENDED_W = 720
TOP_BANNER_RECOMMENDED_H = 120

class AdPlacement(models.Model):
    """
    Top banners por país (y opcionalmente un enlace), con prioridad y vigencia.
    No modifica QR/Event. Se administra desde el Admin.
    """
    country = models.CharField(
        max_length=64,
        help_text="Código o nombre del país (p. ej. 'BO', 'Bolivia')."
    )
    title = models.CharField(
        max_length=128,
        blank=True,
        help_text="Etiqueta interna para identificar el anuncio."
    )
    image = models.ImageField(
        upload_to="ads/",
        blank=True,      # <--- permite crear sin subir imagen
        help_text="Imagen del banner superior (recomendado 720x120)."
    )
    url = models.URLField(
        blank=True,
        help_text="Enlace opcional (se usará si el banner es clicable)."
    )
    priority = models.PositiveIntegerField(
        default=100,
        help_text="Menor número = mayor prioridad."
    )
    active = models.BooleanField(
        default=True,
        help_text="Si está desactivado, no se seleccionará."
    )
    starts_at = models.DateTimeField(
        blank=True, null=True,
        help_text="Inicio de vigencia (opcional)."
    )
    ends_at = models.DateTimeField(
        blank=True, null=True,
        help_text="Fin de vigencia (opcional)."
    )

    class Meta:
        ordering = ["priority", "country", "-starts_at"]
        verbose_name = "Top Banner por país"
        verbose_name_plural = "Top Banners por país"

    def __str__(self):
        label = self.title or self.country
        return f"{label} (prio {self.priority})"

    # --- Utilidades de estado/vigencia ---
    def is_live(self, now=None) -> bool:
        now = now or timezone.now()
        if not self.active:
            return False
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True

    # --- Validaciones de datos (mejores prácticas) ---
    def clean(self):
        # Coherencia temporal
        if self.starts_at and self.ends_at and self.starts_at > self.ends_at:
            raise ValidationError("La fecha de inicio no puede ser posterior a la fecha de fin.")

        # Validación opcional de dimensiones (solo advertimos si es muy distinto)
        if self.image and hasattr(self.image, "file"):
            try:
                self.image.file.seek(0)
                with Image.open(self.image.file) as im:
                    w, h = im.size
                    # relación ~6:1; tolerancia simple
                    if h == 0 or w == 0:
                        raise ValidationError("La imagen del banner no parece válida (ancho/alto 0).")
                    ratio = w / h
                    if ratio < 4.5 or ratio > 8.0:
                        raise ValidationError(
                            f"La relación de aspecto del banner ({w}x{h}) no es la recomendada (~720x120 ≈ 6:1)."
                        )
            except ValidationError:
                raise
            except Exception:
                # No rompemos el guardado si no podemos validar; deja rastro en logs si lo deseas.
                pass

class AdDefaults(models.Model):
    """
    Singleton: valores por defecto que el admin puede controlar.
    - image: banner por defecto (si no hay placement por país)
    - starts_at/ends_at: ventana por defecto
    - grace_minutes: por defecto
    - font_path: ruta relativa o nombre de fuente recomendado
    """
    image = models.ImageField(upload_to="ads/defaults/", blank=True, null=True,
                              help_text="Banner por defecto (720x120). Se usará si no hay AdPlacement por país).")
    starts_at = models.DateTimeField(blank=True, null=True, help_text="Inicio de vigencia por defecto (opcional).")
    ends_at = models.DateTimeField(blank=True, null=True, help_text="Fin de vigencia por defecto (opcional).")
    grace_minutes = models.PositiveIntegerField(default=0, help_text="Minutos de gracia por defecto.")
    font_path = models.CharField(max_length=255, blank=True, default="", help_text="Ruta a fuente TTF (opcional).")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ad Defaults (singleton)"
        verbose_name_plural = "Ad Defaults (singleton)"

    def __str__(self):
        return "Ad Defaults (singleton)"

    # --- singleton helper ---
    @classmethod
    def get_solo(cls):
        obj = cls.objects.first()
        if obj is None:
            # crear con valores vacíos (seguro para migration-first time)
            obj = cls.objects.create()
        return obj

    def clean(self):
        # validación temporal coherente
        if self.starts_at and self.ends_at and self.starts_at > self.ends_at:
            raise ValidationError("starts_at no puede ser posterior a ends_at.")
        # validación opcional de dimensiones (similar a AdPlacement)
        if self.image and hasattr(self.image, "file"):
            try:
                self.image.file.seek(0)
                with Image.open(self.image.file) as im:
                    w, h = im.size
                    if w == 0 or h == 0:
                        raise ValidationError("Imagen inválida.")
                    ratio = w / h
                    if ratio < 4.5 or ratio > 8.0:
                        raise ValidationError("La relación de aspecto no es la recomendada (~6:1).")
            except ValidationError:
                raise
            except Exception:
                pass