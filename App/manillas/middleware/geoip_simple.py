# core/middleware/geoip_trusted_headers.py
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from ipaddress import ip_address, ip_network
import geoip2.database
from pathlib import Path

DB_PATH = Path(settings.BASE_DIR) / "geoip" / "GeoLite2-Country.mmdb"
TRUSTED_PROXY_CIDRS = getattr(settings, "TRUSTED_PROXY_CIDRS",
                              ["127.0.0.1/32", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "82.180.132.0/23",])
TRUSTED_NETS = [ip_network(c) for c in TRUSTED_PROXY_CIDRS]

_reader = None
def get_reader():
    global _reader
    if _reader is None:
        _reader = geoip2.database.Reader(str(DB_PATH))
    return _reader

def is_trusted(remote: str) -> bool:
    try:
        ip = ip_address(remote)
        return any(ip in n for n in TRUSTED_NETS)
    except ValueError:
        return False

def extract_client_ip(request) -> str | None:
    remote = request.META.get("REMOTE_ADDR", "")
    # Si la conexión viene de un proxy confiable, podemos mirar cabeceras:
    if remote and is_trusted(remote):
        # Prioriza cabeceras provistas por CDNs/LB:
        for header in ("HTTP_TRUE_CLIENT_IP", "HTTP_CF_CONNECTING_IP", "HTTP_X_REAL_IP"):
            val = request.META.get(header)
            if val:
                return val.strip()
        # XFF = "ip_origen, proxy1, proxy2, ..."
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
    # Si no hay proxy confiable, usa REMOTE_ADDR
    return remote or None

class TrustedGeoIPMiddleware(MiddlewareMixin):
    def process_request(self, request):
        ip = extract_client_ip(request)
        try:
            resp = get_reader().country(ip) if ip else None
            request.country_code = resp.country.iso_code if resp else None
            request.country_name = resp.country.name if resp else None
        except Exception:
            request.country_code = None
            request.country_name = None
