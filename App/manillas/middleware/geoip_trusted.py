"""
Middleware con manejo básico de reverse proxy:
- Solo confía en X-Forwarded-For si REMOTE_ADDR pertenece a un proxy de confianza.
- En caso contrario usa REMOTE_ADDR directamente.

Configurar en settings.py:
    TRUSTED_PROXY_CIDRS = ["127.0.0.1/32", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
    GEOIP_PATH = BASE_DIR / "geoip"

Sugerencia: en Apache, activar mod_remoteip y evitar parsear XFF en Django.
"""

from django.utils.deprecation import MiddlewareMixin
from django.contrib.gis.geoip2 import GeoIP2
from django.conf import settings
from ipaddress import ip_address, ip_network


def _trusted_networks():
    cidrs = getattr(
        settings,
        "TRUSTED_PROXY_CIDRS",
        ["127.0.0.1/32"],  # por defecto solo loopback
    )
    return [ip_network(c) for c in cidrs]


def _is_trusted(addr: str) -> bool:
    try:
        ip = ip_address(addr)
        return any(ip in net for net in _trusted_networks())
    except ValueError:
        return False


def _client_ip(request) -> str | None:
    """
    Retorna la IP del cliente:
    - Si la conexión proviene de un proxy confiable (REMOTE_ADDR ∈ TRUSTED_PROXY_CIDRS),
      toma el primer valor de X-Forwarded-For.
    - En otro caso, usa REMOTE_ADDR.
    """
    remote = request.META.get("REMOTE_ADDR", "")
    if remote and _is_trusted(remote):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            # XFF = "ip_origen, proxy1, proxy2, ..."
            return xff.split(",")[0].strip()
    return remote or None


class TrustedGeoIPMiddleware(MiddlewareMixin):
    """
    Adjunta a la request:
        request.client_ip   -> str | None (IP deducida)
        request.country_code -> str | None (ej. 'BO')
        request.country_name -> str | None (ej. 'Bolivia')
    """

    def process_request(self, request):
        request.client_ip = _client_ip(request)
        if not request.client_ip:
            request.country_code = None
            request.country_name = None
            return

        try:
            g = GeoIP2()
            data = g.country(request.client_ip)
            request.country_code = data.get("country_code")
            request.country_name = data.get("country_name")
        except Exception:
            request.country_code = None
            request.country_name = None
