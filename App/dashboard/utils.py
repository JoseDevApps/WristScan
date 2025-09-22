# dashboard/utils.py
from .models import AdPlacement, AdDefaults

def get_default_adsettings():
    return AdDefaults.get_solo()

def pick_banner_for_country(country_code: str | None, country_name: str | None):
    """
    Lógica simple: buscar AdPlacement activo y live por country (exact match),
    por prioridad, si none usar AdDefaults.image como fallback.
    Devuelve: (adplacement_or_none, is_default_flag)
    """
    qs = AdPlacement.objects.filter(active=True)
    if country_code:
        # intenta coincidencia por código o por nombre
        q = qs.filter(country__iexact=country_code).order_by("priority", "-starts_at").first()
        if q:
            return q, False
    if country_name:
        q = qs.filter(country__iexact=country_name).order_by("priority", "-starts_at").first()
        if q:
            return q, False
    # fallback global: pick highest priority active global placement (country blank) OR defaults
    q = qs.filter(country="").order_by("priority", "-starts_at").first()
    if q:
        return q, False
    # fallback defaults
    defaults = get_default_adsettings()
    return defaults, True
