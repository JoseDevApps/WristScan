# qrcodes/utils/footer_presets.py
from django.conf import settings

DEFAULTS = {"text": "Uniqbo.com", "bg": "#000000", "fg": "#FFFFFF"}

def get_footer_preset(country_code: str | None, country_name: str | None) -> dict:
    presets = getattr(settings, "FOOTER_PRESETS_BY_COUNTRY", {})
    if country_code and country_code in presets:
        return {**DEFAULTS, **presets[country_code]}
    if country_name and country_name in presets:
        return {**DEFAULTS, **presets[country_name]}
    if "*" in presets:
        return {**DEFAULTS, **presets["*"]}
    return DEFAULTS.copy()
