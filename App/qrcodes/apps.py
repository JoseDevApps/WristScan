from django.apps import AppConfig


class QrcodesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "qrcodes"

    def ready(self):
        import qrcodes.signals  # 👈 importante: así se registran tus signals
