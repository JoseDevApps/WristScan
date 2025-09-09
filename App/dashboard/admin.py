# admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Product, AdPlacement

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

    @admin.display(description="Vista previa")
    def preview(self, obj: AdPlacement):
        if obj.image:
            return format_html('<img src="{}" style="max-width:360px; height:auto; border:1px solid #e5e7eb;" />', obj.image.url)
        return "—"
