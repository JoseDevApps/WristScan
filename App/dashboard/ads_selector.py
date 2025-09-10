# tu_app/ads_selector.py
from typing import Optional
from django.db import models
from django.utils import timezone
from django.core.cache import cache
from .models import AdPlacement  # si usaste paquete models/, importa desde allí

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

def get_banner_for_country(country_code: Optional[str], country_name: Optional[str]) -> Optional[AdPlacement]:
    # 1) code (ej. "BO")
    if country_code:
        k = _KEY.format(k=country_code.upper())
        cached = cache.get(k)
        if cached is not None:
            return cached
        hit = _query_live(country_code)
        cache.set(k, hit, CACHE_TTL_SECONDS)
        if hit:
            return hit
    # 2) name (ej. "Bolivia")
    if country_name:
        k = _KEY.format(k=country_name.lower())
        cached = cache.get(k)
        if cached is not None:
            return cached
        hit = _query_live(country_name)
        cache.set(k, hit, CACHE_TTL_SECONDS)
        if hit:
            return hit
    # 3) (opcional) fallback global con country="*"
    # k = _KEY.format(k="*")
    # cached = cache.get(k)
    # if cached is not None:
    #     return cached
    # hit = _query_live("*")
    # cache.set(k, hit, CACHE_TTL_SECONDS)
    # return hit
    return None
