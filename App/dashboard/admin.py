# admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Product, AdPlacement,AdDefaults
from qrcodes.models import QRCode
admin.site.register(Product)

@admin.register(AdPlacement)
class AdPlacementAdmin(admin.ModelAdmin):
    list_display = ("title", "country", "priority", "active", "starts_at", "ends_at", "preview")
    list_filter = ("country", "active", "starts_at", "ends_at")
    search_fields = ("title", "country", "url")
    ordering = ("priority", "country", "-starts_at")
    readonly_fields = ("preview",)
    fieldsets = (
        (None, {
            "fields": ("title", "country", "priority", "active")
        }),
        ("Creativo", {
            "fields": ("image", "preview", "url"),
            "description": "Sube una imagen ~720x120 para un buen encaje visual."
        }),
        ("Vigencia (opcional)", {
            "classes": ("collapse",),
            "fields": ("starts_at", "ends_at"),
        }),
    )

    @admin.display(description="QRs Gratis asignados")
    def assigned_free_qrs(self, obj: AdPlacement):
        # Contar QR asignados a eventos con free tickets que usan este banner
        count = QRCode.objects.filter(
            enable_top_banner=True,
            top_banner__isnull=False,
            event_fk__ads_enabled=True,
            event_fk__qr_codes__top_banner=obj.image.name if obj.image else None
        ).distinct().count()
        return count

    @admin.display(description="Vista previa")
    def preview(self, obj: AdPlacement):
        if obj.image:
            return format_html('<img src="{}" style="max-width:360px; height:auto; border:1px solid #e5e7eb;" />', obj.image.url)
        return "—"
    


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