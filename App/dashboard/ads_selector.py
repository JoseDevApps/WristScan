# tu_app/ads_selector.py
from typing import Optional
from django.db import models
from django.utils import timezone
from django.core.cache import cache
from .models import AdPlacement, AdDefaults  # importa también AdDefault

CACHE_TTL_SECONDS = 120
_KEY = "adplacement:country:{k}"
_KEY_DEF = "addefault:country:{k}"


def _query_live(country: str):
    now = timezone.now()
    return (
        AdPlacement.objects.filter(active=True, country__iexact=country)
        .filter(models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=now))
        .filter(models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=now))
        .order_by("priority", "country", "-starts_at")
        .first()
    )


def _query_default(country: str):
    """Busca un AdDefault (publicidad por defecto) por país exacto o global."""
    return (
        AdDefaults.objects.filter(country__iexact=country)
        .order_by("priority", "-created_at")
        .first()
    )


def get_banner_for_country(country_code: Optional[str], country_name: Optional[str]):
    # 1) Buscar por código de país (ej. "BO")
    if country_code:
        k = _KEY.format(k=country_code.upper())
        cached = cache.get(k)
        if cached is not None:
            return cached
        hit = _query_live(country_code)
        cache.set(k, hit, CACHE_TTL_SECONDS)
        if hit:
            return hit

    # 2) Buscar por nombre de país (ej. "Bolivia")
    if country_name:
        k = _KEY.format(k=country_name.lower())
        cached = cache.get(k)
        if cached is not None:
            return cached
        hit = _query_live(country_name)
        cache.set(k, hit, CACHE_TTL_SECONDS)
        if hit:
            return hit

    # 3) (opcional) fallback global en AdPlacement con country="*"
    # hit = _query_live("*")
    # if hit:
    #     return hit

    # 4) Si no hay AdPlacement → buscar en AdDefault
    if country_code:
        kd = _KEY_DEF.format(k=country_code.upper())
        cached = cache.get(kd)
        if cached is not None:
            return cached
        hit = _query_default(country_code)
        cache.set(kd, hit, CACHE_TTL_SECONDS)
        if hit:
            return hit

    if country_name:
        kd = _KEY_DEF.format(k=country_name.lower())
        cached = cache.get(kd)
        if cached is not None:
            return cached
        hit = _query_default(country_name)
        cache.set(kd, hit, CACHE_TTL_SECONDS)
        if hit:
            return hit

    # 5) Fallback global en AdDefault (ej. country="*")
    hit = _query_default("*")
    return hit