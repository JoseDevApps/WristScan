# admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Product, AdPlacement,AdDefaults
from qrcodes.models import QRCode
admin.site.register(Product)

# @admin.register(AdPlacement)
# class AdPlacementAdmin(admin.ModelAdmin):
#     list_display = ("title", "country", "priority", "active", "starts_at", "ends_at", "preview")
#     list_filter = ("country", "active", "starts_at", "ends_at")
#     search_fields = ("title", "country", "url")
#     ordering = ("priority", "country", "-starts_at")
#     readonly_fields = ("preview",)
#     fieldsets = (
#         (None, {
#             "fields": ("title", "country", "priority", "active")
#         }),
#         ("Creativo", {
#             "fields": ("image", "preview", "url"),
#             "description": "Sube una imagen ~720x120 para un buen encaje visual."
#         }),
#         ("Vigencia (opcional)", {
#             "classes": ("collapse",),
#             "fields": ("starts_at", "ends_at"),
#         }),
#     )

#     @admin.display(description="QRs Gratis con Ads asignados")
#     def assigned_qrs_count(self, obj: AdPlacement):
#         """
#         Cuenta los QR asignados a eventos con ads_enabled=True
#         y que usan banners activos del mismo país que el AdPlacement.
#         """
#         if not obj.image:
#             return 0

#         # Contar QR que tienen banner activo
#         return QRCode.objects.filter(
#             enable_top_banner=True,
#             event_fk__ads_enabled=True
#         ).exclude(top_banner__isnull=True).count()

#     @admin.display(description="Vista previa")
#     def preview(self, obj: AdPlacement):
#         if obj.image:
#             return format_html('<img src="{}" style="max-width:360px; height:auto; border:1px solid #e5e7eb;" />', obj.image.url)
#         return "—"
    
@admin.register(AdPlacement)
class AdPlacementAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "country",
        "priority",
        "active",
        "starts_at",
        "ends_at",
        "preview",
        "assigned_qrs_count",
        "default_assigned_qrs_count",
    )
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

    @admin.display(description="Vista previa")
    def preview(self, obj: AdPlacement):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width:360px; height:auto; border:1px solid #e5e7eb;" />',
                obj.image.url
            )
        return "—"

    @admin.display(description="QRs Gratis con Ads asignados")
    def assigned_qrs_count(self, obj: AdPlacement):
        """
        Cuenta los QR que:
         - tienen enable_top_banner=True
         - pertenecen a eventos con ads_enabled=True
         - y cuyo top_banner coincide con la imagen del AdPlacement (ruta o basename)
        """
        if not obj or not getattr(obj, "image", None):
            return 0

        img_name = getattr(obj.image, "name", None)
        if not img_name:
            return 0

        basename = os.path.basename(img_name)

        return QRCode.objects.filter(
            enable_top_banner=True,
            event_fk__ads_enabled=True
        ).filter(
            Q(top_banner=img_name) | Q(top_banner__endswith=basename)
        ).count()

    @admin.display(description="QRs asignados con banner por defecto")
    def default_assigned_qrs_count(self, obj: AdPlacement):
        """
        Cuenta QR que usan el banner por defecto (AdDefaults.image).
        Útil para saber cuántos QR caen al fallback.
        """
        defaults = AdDefaults.objects.first()
        if not defaults or not getattr(defaults, "image", None):
            return 0

        default_name = getattr(defaults.image, "name", None)
        if not default_name:
            return 0

        default_basename = os.path.basename(default_name)

        return QRCode.objects.filter(
            enable_top_banner=True,
            event_fk__ads_enabled=True
        ).filter(
            Q(top_banner=default_name) | Q(top_banner__endswith=default_basename)
        ).count()


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


