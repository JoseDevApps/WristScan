# middleware/geoip_simple.py
import geoip2.database
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
import os

class SimpleGeoIPMiddleware(MiddlewareMixin):
    def process_request(self, request):
        ip = request.META.get("REMOTE_ADDR")
        db_path = os.path.join(settings.BASE_DIR, "geoip", "GeoLite2-Country.mmdb")

        try:
            reader = geoip2.database.Reader(db_path)
            resp = reader.country(ip)
            request.country_code = resp.country.iso_code
            request.country_name = resp.country.name
            reader.close()
        except Exception:
            request.country_code = None
            request.country_name = None
