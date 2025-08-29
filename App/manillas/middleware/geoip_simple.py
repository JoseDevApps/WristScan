# # middleware/geoip_simple.py
# import geoip2.database
# from django.utils.deprecation import MiddlewareMixin
# from django.conf import settings
# import os

# class SimpleGeoIPMiddleware(MiddlewareMixin):
#     def process_request(self, request):
#         ip = request.META.get("REMOTE_ADDR")
#         db_path = os.path.join(settings.BASE_DIR, "geoip", "GeoLite2-Country.mmdb")

#         try:
#             reader = geoip2.database.Reader(db_path)
#             resp = reader.country(ip)
#             request.country_code = resp.country.iso_code
#             request.country_name = resp.country.name
#             reader.close()
#         except Exception:
#             request.country_code = None
#             request.country_name = None

# core/middleware/geoip_realip.py
from django.utils.deprecation import MiddlewareMixin
import geoip2.database
from django.conf import settings
from pathlib import Path

DB_PATH = Path(settings.BASE_DIR) / "geoip" / "GeoLite2-Country.mmdb"
_reader = None
def get_reader():
    global _reader
    if _reader is None:
        _reader = geoip2.database.Reader(str(DB_PATH))
    return _reader

class GeoIPRealIPMiddleware(MiddlewareMixin):
    def process_request(self, request):
        ip = request.META.get("REMOTE_ADDR")  # ← ya es la IP real, gracias a mod_remoteip
        try:
            resp = get_reader().country(ip)
            request.country_code = resp.country.iso_code
            request.country_name = resp.country.name
        except Exception:
            request.country_code = None
            request.country_name = None

