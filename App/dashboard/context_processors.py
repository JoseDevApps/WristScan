# tu_app/context_processors.py
from .ads_selector import get_banner_for_country
from django.conf import settings

def top_banner_context(request):
    """
    Inyecta 'current_ad', 'current_ad_url', 'current_ad_image_url'
    solo si FEATURE_TOP_BANNER_RUNTIME está activo.
    """
    if not getattr(settings, "FEATURE_TOP_BANNER_RUNTIME", False):
        return {"current_ad": None, "current_ad_url": "", "current_ad_image_url": ""}

    cc = getattr(request, "country_code", None)
    cn = getattr(request, "country_name", None)

    ad = None
    try:
        ad = get_banner_for_country(cc, cn)
    except Exception:
        ad = None

    return {
        "current_ad": ad,
        "current_ad_url": getattr(ad, "url", "") if ad else "",
        "current_ad_image_url": ad.image.url if (ad and ad.image) else "",
    }
