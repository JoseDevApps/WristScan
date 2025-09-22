from django.utils import timezone
from qrcodes.models import QRCode
from .models import  AdPlacement, AdDefaults

def cleanup_expired_free_qrs():
    now = timezone.now()

    # --- 1️⃣ Obtener QR gratuitos activos ---
    free_qrs = QRCode.objects.filter(enable_top_banner=True)

    count = 0

    for qr in free_qrs.select_related('event_fk'):
        event = qr.event_fk
        country_code = getattr(event, 'country_code', None)  # asumir campo en Event

        # --- 2️⃣ Buscar AdPlacement para país ---
        ad = AdPlacement.objects.filter(
            country=country_code,
            active=True
        ).first()  # tomamos la de mayor prioridad por Meta.ordering

        # --- 3️⃣ Revisar vigencia ---
        expired = False
        if ad:
            if (ad.starts_at and ad.starts_at > now) or (ad.ends_at and ad.ends_at < now):
                expired = True
        else:
            # No hay AdPlacement, revisar AdDefaults
            ad_default = AdDefaults.get_solo()
            if ad_default.image:  # tiene banner default
                if (ad_default.starts_at and ad_default.starts_at > now) or \
                   (ad_default.ends_at and ad_default.ends_at < now):
                    expired = True
            else:
                # no hay banner default, consideramos expirado para limpiar
                expired = True

        # --- 4️⃣ Limpiar QR si expiró ---
        if expired:
            qr.enable_top_banner = False
            qr.top_banner = None
            qr.footer_text = ""
            qr.footer_bg = "#111111"
            qr.footer_fg = "#FFFFFF"
            qr.save()
            count += 1

    return count