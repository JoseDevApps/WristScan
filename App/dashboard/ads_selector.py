# tu_app/ads_selector.py
from typing import Optional
from django.db import models
from django.utils import timezone
from django.core.cache import cache
from .models import AdPlacement, AdDefaults  # importa también AdDefault

CACHE_TTL_SECONDS = 120
_KEY = "adplacement:country:{k}"

def _query_live(country: str):
    now = timezone.now()
    return (
        AdPlacement.objects.filter(active=True, country__iexact=country)
        .filter(models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=now))
        .filter(models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=now))
        .order_by("priority", "country", "-starts_at")
        .first()
    )

def get_banner_for_country(country_code: Optional[str], country_name: Optional[str]):
    """Devuelve el AdPlacement activo o, si no hay, el AdDefault correspondiente."""
    # --- 1) buscar por código ---
    if country_code:
        k = _KEY.format(k=country_code.upper())
        cached = cache.get(k)
        if cached is not None:
            return cached
        hit = _query_live(country_code)
        if hit:
            cache.set(k, hit, CACHE_TTL_SECONDS)
            return hit

    # --- 2) buscar por nombre ---
    if country_name:
        k = _KEY.format(k=country_name.lower())
        cached = cache.get(k)
        if cached is not None:
            return cached
        hit = _query_live(country_name)
        if hit:
            cache.set(k, hit, CACHE_TTL_SECONDS)
            return hit

    # --- 3) fallback a AdDefault ---
    default_ad = None
    if country_code:
        default_ad = AdDefaults.objects.filter(country__iexact=country_code).first()
    if not default_ad and country_name:
        default_ad = AdDefaults.objects.filter(country__iexact=country_name).first()
    
    return default_ad  # puede ser None si tampoco hay AdDefault
