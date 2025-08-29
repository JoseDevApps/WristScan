"""
Middleware simple para adjuntar país a la request usando GeoLite2.

Requisitos:
- INSTALLED_APPS incluye "django.contrib.gis"
- GEOIP_PATH en settings apunta a la carpeta que contiene el .mmdb
    GEOIP_PATH = BASE_DIR / "geoip"
- Archivo GeoLite2-Country.mmdb dentro de GEOIP_PATH
"""

from django.utils.deprecation import MiddlewareMixin
from django.contrib.gis.geoip2 import GeoIP2


class SimpleGeoIPMiddleware(MiddlewareMixin):
    """
    Adjunta a la request:
        request.country_code -> str | None (ej. 'BO')
        request.country_name -> str | None (ej. 'Bolivia')
    Usa REMOTE_ADDR tal cual lo recibe Django. Si estás detrás de proxy,
    considera usar mod_remoteip en Apache para que REMOTE_ADDR sea la IP real.
    """

    def process_request(self, request):
        ip = request.META.get("REMOTE_ADDR")
        try:
            g = GeoIP2()  # usará settings.GEOIP_PATH
            data = g.country(ip)
            request.country_code = data.get("country_code")
            request.country_name = data.get("country_name")
        except Exception:
            # Puede fallar por:
            # - DB no encontrada
            # - IP privada/no enrutable
            # - AddressNotFoundError
            request.country_code = None
            request.country_name = None
