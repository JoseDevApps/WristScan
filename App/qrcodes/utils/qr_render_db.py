# qrcodes/utils/qr_render_db.py
from __future__ import annotations
from typing import Optional
from pathlib import Path
from io import BytesIO
from datetime import datetime, timezone, timedelta

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont, ImageOps
import qrcode

from qrcodes.models import QRCode
from dashboard.ads_selector import get_banner_for_country

CANVAS_W, CANVAS_H = 720, 1330
TOP_H = 120
FOOTER_H = 60
CENTRAL_H = CANVAS_H - TOP_H - FOOTER_H
QR_SIZE = 330

UTC_MINUS_4 = timezone(timedelta(hours=-4))
ISO_LOCAL_FMT = "%Y-%m-%dT%H:%M:%S"

def parse_iso_utc_minus4(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    dt = datetime.strptime(s, ISO_LOCAL_FMT)
    return dt.replace(tzinfo=UTC_MINUS_4)

def now_utc_minus4() -> datetime:
    return datetime.now(UTC_MINUS_4)

def expires_at_with_grace(valid_until: Optional[datetime], grace_minutes: int) -> Optional[datetime]:
    if not valid_until:
        return None
    return valid_until + timedelta(minutes=grace_minutes or 0)

def fit_exact(img: Image.Image, size):
    return ImageOps.fit(img.convert("RGBA"), size, method=Image.LANCZOS)

def load_image_or_color(field_or_path, fallback_rgba=(235, 235, 235, 255), size=(100, 100)):
    try:
        if hasattr(field_or_path, "open"):
            field_or_path.open()
            with Image.open(field_or_path) as im:
                return fit_exact(im, size)
        if field_or_path:
            p = Path(str(field_or_path))
            if p.exists():
                with Image.open(p) as im:
                    return fit_exact(im, size)
    except Exception:
        pass
    return Image.new("RGBA", size, fallback_rgba)

def make_qr(data: str, size: int = QR_SIZE) -> Image.Image:
    qr_raw = qrcode.make(data)
    return qr_raw.resize((size, size), Image.NEAREST).convert("RGBA")

def draw_footer(canvas: Image.Image, qr_id_display: str, font_path: Optional[str], valid_until: Optional[datetime]):
    draw = ImageDraw.Draw(canvas)
    y0, y1, h = CANVAS_H - FOOTER_H, CANVAS_H, FOOTER_H
    black, white = (0, 0, 0, 255), (255, 255, 255, 255)

    L0, L1 = 0, CANVAS_W // 3
    C0, C1 = L1, (CANVAS_W * 2) // 3
    R0, R1 = C1, CANVAS_W

    draw.rectangle([L0, y0, L1, y1], fill=black)
    draw.rectangle([C0, y0, C1, y1], fill=white)
    draw.rectangle([R0, y0, R1, y1], fill=black)

    draw.polygon([(L1 - 15, y0), (L1 + 15, y0), (L1 - 15, y1), (L1 - 45, y1)], fill=black)
    draw.polygon([(C1 - 15, y0), (C1 + 15, y0), (C1 + 45, y1), (C1 + 15, y1)], fill=black)

    try:
        font = ImageFont.truetype(font_path, 22) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    left_text = "Uniqbo.com"
    th = draw.textbbox((0, 0), left_text, font=font)[3]
    draw.text((20, y0 + (h - th) // 2), left_text, font=font, fill=white)

    center_text = f"ID {qr_id_display}"
    bbox = draw.textbbox((0, 0), center_text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    cx = C0 + (C1 - C0 - tw) // 2
    cy = y0 + (h - th) // 2
    draw.text((cx, cy), center_text, font=font, fill=black)

    if valid_until:
        right_text = valid_until.strftime("%d/%m %H:%M")
        bbox = draw.textbbox((0, 0), right_text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        rx = R1 - tw - 20
        ry = y0 + (h - th) // 2
        draw.text((rx, ry), right_text, font=font, fill=white)

def compose_qr_from_db(
    qr: QRCode,
    *,
    country_code: Optional[str] = None,
    country_name: Optional[str] = None,
    valid_from_str: Optional[str] = None,
    valid_until_str: Optional[str] = None,
    grace_minutes: int = 0,
    font_path: Optional[str] = None,
) -> dict:
    valid_from  = parse_iso_utc_minus4(valid_from_str)
    valid_until = parse_iso_utc_minus4(valid_until_str)

    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (255, 255, 255, 255))

    ad = get_banner_for_country(country_code, country_name)
    top = load_image_or_color(ad.image if ad and ad.image else None,
                              fallback_rgba=(20, 20, 20, 255), size=(CANVAS_W, TOP_H))
    canvas.paste(top, (0, 0), top)

    central = load_image_or_color(getattr(qr, "mask_banner", None),
                                  fallback_rgba=(235, 235, 235, 255), size=(CANVAS_W, CENTRAL_H))
    canvas.paste(central, (0, TOP_H), central)

    qr_img = make_qr(qr.data, size=QR_SIZE)
    qr_x = (CANVAS_W - QR_SIZE) // 2
    qr_y = (CANVAS_H - FOOTER_H) - QR_SIZE
    canvas.paste(qr_img, (qr_x, qr_y), qr_img)

    draw_footer(canvas, str(qr.id), font_path, valid_until=valid_until)

    out_rgb = Image.new("RGB", (CANVAS_W, CANVAS_H), (255, 255, 255))
    out_rgb.paste(canvas, mask=canvas.split()[-1])
    buf = BytesIO()
    out_rgb.save(buf, format="PNG", optimize=True)
    buf.seek(0)

    filename = qr.image.name if (qr.image and qr.image.name) else f"qrcodes/qr_{qr.id}_.png"
    try:
        if qr.image and qr.image.storage.exists(qr.image.name):
            qr.image.storage.delete(qr.image.name)
    except Exception:
        pass
    qr.image.save(filename, ContentFile(buf.read()), save=True)

    now_ = now_utc_minus4()
    is_valid_now = True
    if valid_from and now_ < valid_from:
        is_valid_now = False
    end = expires_at_with_grace(valid_until, grace_minutes)
    if end and now_ > end:
        is_valid_now = False

    return {
        "qr_id": qr.id,
        "file": qr.image.name,
        "valid_from": valid_from.isoformat() if valid_from else "",
        "valid_until": valid_until.isoformat() if valid_until else "",
        "grace_minutes": grace_minutes,
        "generated_at": now_.isoformat(),
        "is_valid_now": is_valid_now,
    }
