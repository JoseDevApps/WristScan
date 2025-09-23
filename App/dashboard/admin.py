# admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Product, AdPlacement,AdDefaults
from qrcodes.models import QRCode, Event
from django.db.models import Q, Count

import os
admin.site.register(Product)

    
@admin.register(AdPlacement)
class AdPlacementAdmin(admin.ModelAdmin):
    list_display = (
        "title", "country", "priority", "active", "starts_at", "ends_at",
        "preview", "assigned_qrs_count", "default_assigned_qrs_count",
    )
    readonly_fields = ("preview",)

    @admin.display(description="Vista previa")
    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-width:360px; height:auto; border:1px solid #e5e7eb;" />', obj.image.url)
        return "—"

    @admin.display(description="QRs Gratis con Ads asignados")
    def assigned_qrs_count(self, obj: AdPlacement):
        """
        Cuenta QR que:
         - están asociados a EVENTS marcados ads_enabled=True
         - y entre esos QR tienen enable_top_banner=True y top_banner coincide con este AdPlacement.image
        """
        if not obj or not getattr(obj, "image", None):
            return 0

        img_name = getattr(obj.image, "name", None)
        if not img_name:
            return 0
        basename = os.path.basename(img_name)

        # Buscamos Events activos (ads_enabled=True) que tengan QR cuya top_banner coincida
        # y contamos los QR (distinct) que cumplen.
        qs = Event.objects.filter(
            ads_enabled=True,
            qr_codes__enable_top_banner=True
        ).filter(
            Q(qr_codes__top_banner=img_name) | Q(qr_codes__top_banner__endswith=basename)
        ).annotate(cnt=Count("qr_codes", distinct=True))

        # Sumamos los contadores (normalmente será 1 registro con la agregación)
        total = sum(item.cnt for item in qs)
        return total

    @admin.display(description="QRs asignados con banner por defecto")
    def default_assigned_qrs_count(self, obj: AdPlacement):
        """
        Cuenta QR que usan el banner por defecto definido en AdDefaults.
        """
        defaults = AdDefaults.objects.first()
        if not defaults or not getattr(defaults, "image", None):
            return 0
        default_name = getattr(defaults.image, "name", None)
        if not default_name:
            return 0
        default_basename = os.path.basename(default_name)

        qs = Event.objects.filter(
            ads_enabled=True,
            qr_codes__enable_top_banner=True
        ).filter(
            Q(qr_codes__top_banner=default_name) | Q(qr_codes__top_banner__endswith=default_basename)
        ).annotate(cnt=Count("qr_codes", distinct=True))

        total = sum(item.cnt for item in qs)
        return total


@admin.register(AdDefaults)
class AdDefaultsAdmin(admin.ModelAdmin):
    # change_form_template = "admin/addefaults_change_form.html"  # opcional si quieres UI custom
    list_display = ("__str__", "starts_at", "ends_at", "grace_minutes", "updated_at")
    readonly_fields = ("preview_banner",)
    fieldsets = (
        (None, {"fields": ("image", "preview_banner")}),
        ("Vigencia por defecto", {"fields": ("starts_at", "ends_at", "grace_minutes")}),
        ("Fuente por defecto", {"fields": ("font_path",)}),
    )

    def has_add_permission(self, request):
        # bloquea añadir múltiples; permitimos solo editar la existente
        return False if AdDefaults.objects.exists() else True

    def preview_banner(self, obj):
        if obj and obj.image:
            return f'<img src="{obj.image.url}" style="max-width:300px; max-height:80px"/>'
        return "(no banner)"
    preview_banner.allow_tags = True
    preview_banner.short_description = "Preview"


