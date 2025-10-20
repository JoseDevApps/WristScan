# # qrcodes/utils/qr_render_db.py
# from __future__ import annotations
# from typing import Optional, Tuple
# from io import BytesIO
# from datetime import datetime, timezone, timedelta

# from django.core.files.storage import default_storage
# from django.core.files.base import ContentFile
# from PIL import Image, ImageDraw, ImageFont, ImageOps
# import qrcode

# from qrcodes.models import QRCode
# from dashboard.ads_selector import get_banner_for_country

# # --- Constantes del lienzo ---
# CANVAS_W, CANVAS_H = 720, 1330
# TOP_H = 120
# FOOTER_H = 60
# CENTRAL_H = CANVAS_H - TOP_H - FOOTER_H  # 1150
# QR_SIZE = 330

# # --- Zona horaria: UTC-4 ---
# UTC_MINUS_4 = timezone(timedelta(hours=-4))
# ISO_LOCAL_FMT = "%Y-%m-%dT%H:%M:%S"

# # ---------- Helpers de tiempo ----------
# def parse_iso_utc_minus4(s: Optional[str]) -> Optional[datetime]:
#     if not s:
#         return None
#     dt = datetime.strptime(s, ISO_LOCAL_FMT)
#     return dt.replace(tzinfo=UTC_MINUS_4)

# def now_utc_minus4() -> datetime:
#     return datetime.now(UTC_MINUS_4)

# def expires_at_with_grace(valid_until: Optional[datetime], grace_minutes: int) -> Optional[datetime]:
#     if not valid_until:
#         return None
#     return valid_until + timedelta(minutes=grace_minutes or 0)

# # ---------- Helpers gráficos / storage ----------
# def fit_exact(img: Image.Image, size: Tuple[int, int]):
#     return ImageOps.fit(img.convert("RGBA"), size, method=Image.LANCZOS)

# def _open_storage_image(name_or_field, size: Tuple[int, int], fallback_rgba=(235, 235, 235, 255)) -> Image.Image:
#     """
#     Abre una imagen desde default_storage a partir de:
#       - ImageField / FieldFile (usa .name)
#       - string (name relativo en MEDIA)
#     Si no existe o falla, devuelve un sólido del color 'fallback_rgba'.
#     """
#     # 1) Resolver el 'name'
#     name = None
#     if name_or_field is None:
#         return Image.new("RGBA", size, fallback_rgba)

#     try:
#         # ImageField / FieldFile
#         if hasattr(name_or_field, "name") and name_or_field.name:
#             name = name_or_field.name
#         # string
#         elif isinstance(name_or_field, str) and name_or_field.strip():
#             name = name_or_field.strip()
#     except Exception:
#         name = None

#     if not name:
#         return Image.new("RGBA", size, fallback_rgba)

#     # 2) Abrir desde storage
#     try:
#         if default_storage.exists(name):
#             with default_storage.open(name, "rb") as fh:
#                 with Image.open(fh) as im:
#                     return fit_exact(im, size)
#     except Exception:
#         pass

#     return Image.new("RGBA", size, fallback_rgba)

# def _open_font(font_path: Optional[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
#     """
#     Intenta abrir una fuente TrueType desde:
#       - Ruta local de filesystem
#       - Nombre relativo en default_storage (MEDIA)
#     Si falla, usa la fuente por defecto.
#     """
#     if not font_path:
#         return ImageFont.load_default()
#     # 1) Intentar como ruta en storage
#     try:
#         if default_storage.exists(font_path):
#             with default_storage.open(font_path, "rb") as fh:
#                 return ImageFont.truetype(BytesIO(fh.read()), size)
#     except Exception:
#         pass
#     # 2) Intentar como ruta local
#     try:
#         return ImageFont.truetype(font_path, size)
#     except Exception:
#         return ImageFont.load_default()

# def make_qr(data: str, size: int = QR_SIZE) -> Image.Image:
#     qr_raw = qrcode.make(data)
#     return qr_raw.resize((size, size), Image.NEAREST).convert("RGBA")

# # ---------- Footer 3 columnas (dinámico) ----------
# def _parse_hex_color(hexstr: str, default=(0, 0, 0, 255)):
#     try:
#         h = hexstr.strip().lstrip("#")
#         if len(h) == 6:
#             return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)
#     except Exception:
#         pass
#     return default

# def draw_footer(
#     canvas: Image.Image,
#     *,
#     qr_id_display: str,
#     font_path: Optional[str],
#     valid_until: Optional[datetime],
#     footer_text: str = "",
#     footer_bg: str = "#111111",
#     footer_fg: str = "#FFFFFF",
# ):
#     """
#     Footer 60px en 3 columnas:
#       - Izquierda: 'Uniqbo.com' (blanco sobre negro fijo)
#       - Centro: 'ID <id>' + footer_text (negro sobre blanco)
#       - Derecha: 'DD/MM HH:MM' (validez), blanco sobre negro
#     Con pliegues ↘ y ↗.
#     Colores del centro/derecha personalizables vía footer_bg/footer_fg (solo aplican al texto central; los fondos L/C/R se mantienen negro/blanco/negro).
#     """
#     draw = ImageDraw.Draw(canvas)
#     y0, y1, h = CANVAS_H - FOOTER_H, CANVAS_H, FOOTER_H
#     black, white = (0, 0, 0, 255), (255, 255, 255, 255)

#     L0, L1 = 0, CANVAS_W // 3
#     C0, C1 = L1, (CANVAS_W * 2) // 3
#     R0, R1 = C1, CANVAS_W

#     # Fondos fijos (negro, blanco, negro)
#     draw.rectangle([L0, y0, L1, y1], fill=black)
#     draw.rectangle([C0, y0, C1, y1], fill=white)
#     draw.rectangle([R0, y0, R1, y1], fill=black)

#     # Pliegues
#     draw.polygon([(L1 - 15, y0), (L1 + 15, y0), (L1 - 15, y1), (L1 - 45, y1)], fill=black)
#     draw.polygon([(C1 - 15, y0), (C1 + 15, y0), (C1 + 45, y1), (C1 + 15, y1)], fill=black)

#     font = _open_font(font_path, 22)

#     # Izquierda: marca fija
#     left_text = "Uniqbo.com"
#     th = draw.textbbox((0, 0), left_text, font=font)[3]
#     draw.text((20, y0 + (h - th) // 2), left_text, font=font, fill=white)

#     # Centro: ID + footer_text (texto en color 'footer_bg' o negro? tu requirement decía negro sobre blanco)
#     # Mantengo negro sobre blanco como en tu especificación, y footer_text adjunto si viene:
#     center_text = f"ID {qr_id_display}"
#     if footer_text:
#         center_text = f"{center_text}  {footer_text}"
#     bbox = draw.textbbox((0, 0), center_text, font=font)
#     tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
#     cx = C0 + (C1 - C0 - tw) // 2
#     cy = y0 + (h - th) // 2
#     draw.text((cx, cy), center_text, font=font, fill=black)

#     # Derecha: caducidad
#     if valid_until:
#         right_text = valid_until.strftime("%d/%m %H:%M")
#         bbox = draw.textbbox((0, 0), right_text, font=font)
#         tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
#         rx = R1 - tw - 20
#         ry = y0 + (h - th) // 2
#         draw.text((rx, ry), right_text, font=font, fill=white)

# # ---------- Render principal desde DB ----------
# def compose_qr_from_db(
#     qr: QRCode,
#     *,
#     country_code: Optional[str] = None,
#     country_name: Optional[str] = None,
#     valid_from_str: Optional[str] = None,
#     valid_until_str: Optional[str] = None,
#     grace_minutes: int = 0,
#     font_path: Optional[str] = None,
# ) -> dict:
#     """
#     Renderiza un PNG 720x1330 para un QR existente utilizando:
#       - qr.mask_banner  (string o ImageField) para el área central
#       - qr.enable_top_banner + qr.top_banner + get_banner_for_country(...) para el banner superior
#       - qr.footer_* para personalizar el centro del footer
#       - valid_from/until/grace (opcional) para estado de validez
#     Guarda el PNG en qr.image (reemplazando si existe).
#     """
#     valid_from  = parse_iso_utc_minus4(valid_from_str)
#     valid_until = parse_iso_utc_minus4(valid_until_str)

#     # Lienzo base
#     canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (255, 255, 255, 255))

#     # --- TOP banner ---
#     top_img = Image.new("RGBA", (CANVAS_W, TOP_H), (255, 255, 255, 255))
#     if getattr(qr, "enable_top_banner", True):
#         # Prioridad: banner específico del QR
#         if getattr(qr, "top_banner", None):
#             top_img = _open_storage_image(qr.top_banner, (CANVAS_W, TOP_H), fallback_rgba=(255, 255, 255, 255))
#         else:
#             # Si no hay banner en QR, intentar por país (si nos pasan país; si no, igual se puede intentar)
#             try:
#                 ad = get_banner_for_country(country_code, country_name)
#             except Exception:
#                 ad = None
#             if ad and getattr(ad, "image", None):
#                 top_img = _open_storage_image(ad.image, (CANVAS_W, TOP_H), fallback_rgba=(255, 255, 255, 255))
#     # si enable_top_banner=False → queda blanco por diseño
#     canvas.paste(top_img, (0, 0), top_img)

#     # --- Área central (máscara) ---
#     central_img = _open_storage_image(
#         getattr(qr, "mask_banner", None),
#         (CANVAS_W, CENTRAL_H),
#         fallback_rgba=(235, 235, 235, 255)
#     )
#     canvas.paste(central_img, (0, TOP_H), central_img)

#     # --- QR code ---
#     qr_img = make_qr(qr.data, size=QR_SIZE)
#     qr_x = (CANVAS_W - QR_SIZE) // 2
#     qr_y = (CANVAS_H - FOOTER_H) - QR_SIZE
#     canvas.paste(qr_img, (qr_x, qr_y), qr_img)

#     # --- Footer dinámico ---
#     footer_text = getattr(qr, "footer_text", "") or ""
#     footer_bg   = getattr(qr, "footer_bg", "#111111") or "#111111"  # (no se usa para el fondo por diseño)
#     footer_fg   = getattr(qr, "footer_fg", "#FFFFFF") or "#FFFFFF"  # (color texto centro si quisieras)
#     draw_footer(
#         canvas,
#         qr_id_display=str(qr.id),
#         font_path=font_path,
#         valid_until=valid_until,
#         footer_text=footer_text,
#         footer_bg=footer_bg,
#         footer_fg=footer_fg,
#     )

#     # --- Guardar en PNG (RGB) ---
#     out_rgb = Image.new("RGB", (CANVAS_W, CANVAS_H), (255, 255, 255))
#     out_rgb.paste(canvas, mask=canvas.split()[-1])
#     buf = BytesIO()
#     out_rgb.save(buf, format="PNG", optimize=True)
#     buf.seek(0)

#     filename = qr.image.name if (qr.image and qr.image.name) else f"qrcodes/qr_{qr.id}_.png"
#     # Reemplazar si existe
#     try:
#         if qr.image and qr.image.storage.exists(qr.image.name):
#             qr.image.storage.delete(qr.image.name)
#     except Exception:
#         pass
#     qr.image.save(filename, ContentFile(buf.read()), save=True)

#     # --- Estado de validez ahora ---
#     now_ = now_utc_minus4()
#     is_valid_now = True
#     if valid_from and now_ < valid_from:
#         is_valid_now = False
#     end = expires_at_with_grace(valid_until, grace_minutes)
#     if end and now_ > end:
#         is_valid_now = False

#     return {
#         "qr_id": qr.id,
#         "file": qr.image.name,
#         "valid_from": valid_from.isoformat() if valid_from else "",
#         "valid_until": valid_until.isoformat() if valid_until else "",
#         "grace_minutes": grace_minutes,
#         "generated_at": now_.isoformat(),
#         "is_valid_now": is_valid_now,
#     }

# qrcodes/utils/qr_render_db.py
from __future__ import annotations
from typing import Optional, Union
from io import BytesIO
from datetime import datetime, timezone, timedelta
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageDraw, ImageFont, ImageOps
import qrcode
from PIL import Image, ImageOps

from qrcodes.models import QRCode
from dashboard.ads_selector import get_banner_for_country
from pathlib import Path
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
    return ImageOps.fit(img.convert("RGBA"), size, method=Image.Resampling.LANCZOS)

def _open_from_storage_or_field(field_or_path: Union[str, object]) -> Optional[Image.Image]:
    """
    Abre una imagen ya sea desde un FileField (tiene .open/.read) o desde una ruta relativa en default_storage.
    Devuelve PIL.Image o None si falla.
    """
    try:
        # FileField con .open()
        if hasattr(field_or_path, "open"):
            field_or_path.open()
            with Image.open(field_or_path) as im:
                return im.convert("RGBA")
        # Ruta relativa (str) en storage
        if isinstance(field_or_path, str) and field_or_path:
            if default_storage.exists(field_or_path):
                with default_storage.open(field_or_path, "rb") as fh:
                    with Image.open(fh) as im:
                        return im.convert("RGBA")
    except Exception:
        pass
    return None

# def load_image_or_color(field_or_path, fallback_rgba=(235, 235, 235, 255), size=(100, 100)):
#     im = _open_from_storage_or_field(field_or_path)
#     if im is None:
#         return Image.new("RGBA", size, fallback_rgba)
#     return fit_exact(im, size)

def load_image_or_color(field_or_path,
                        fallback_rgba=(235, 235, 235, 255),
                        size=(100, 100)) -> Image.Image:
    """
    Carga una imagen desde:
      - FieldFile (tiene .open())
      - nombre (str) en default_storage
      - ruta absoluta local (último recurso)
    """
    try:
        if hasattr(field_or_path, "open"):
            field_or_path.open()
            with Image.open(field_or_path) as im:
                return ImageOps.fit(im.convert("RGBA"), size, method=Image.LANCZOS)

        if isinstance(field_or_path, str) and field_or_path.strip():
            name = field_or_path.strip()
            if default_storage.exists(name):
                with default_storage.open(name, "rb") as fh:
                    with Image.open(fh) as im:
                        return ImageOps.fit(im.convert("RGBA"), size, method=Image.LANCZOS)

            p = Path(name)
            if p.exists():
                with Image.open(p) as im:
                    return ImageOps.fit(im.convert("RGBA"), size, method=Image.LANCZOS)
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

    # Fondo negro completo
    draw.rectangle([0, y0, CANVAS_W, y1], fill=black)

    # ⚙️ Polígono central en forma de "V" invertida
    #     ┌───────────────┐
    #     │               │
    #     └──────▼────────┘
    v_depth = 20  # profundidad de la muesca hacia adentro
    center_x = CANVAS_W // 2
    white_triangle = [
    (CANVAS_W // 3, y1),        # base izquierda en la parte inferior
    (CANVAS_W * 2 // 3, y1),    # base derecha
    (center_x, y1 - v_depth)    # punta hacia arriba (hacia adentro del footer)
    ]
    draw.polygon(white_triangle, fill=white)

    # 📍 Tip: ajusta v_depth para hacer la “V” más pronunciada o más suave

    # Fuente más grande para el ID
    try:
        font_large = ImageFont.truetype(font_path, 40) if font_path else ImageFont.load_default()
    except Exception:
        font_large = ImageFont.load_default()
    try:
        font_small = ImageFont.truetype(font_path, 40) if font_path else ImageFont.load_default()
    except Exception:
        font_small = ImageFont.load_default()

    # Texto izquierdo (blanco sobre negro)
    left_text = "Uniqbo.com"
    bbox = draw.textbbox((0, 0), left_text, font=font_small)
    th = bbox[3] - bbox[1]
    draw.text((20, y0 + (h - th) // 2), left_text, font=font_small, fill=white)

    # Texto central (negro sobre blanco dentro del triángulo)
    center_text = f"ID {qr_id_display}"
    bbox = draw.textbbox((0, 0), center_text, font=font_large)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    cx = (CANVAS_W - tw) // 2
    cy = y0 + (h - th) // 2
    draw.text((cx, cy), center_text, font=font_large, fill=black)

    # Texto derecho (blanco sobre negro)
    if valid_until:
        right_text = valid_until.strftime("%d/%m %H:%M")
        bbox = draw.textbbox((0, 0), right_text, font=font_small)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        rx = CANVAS_W - tw - 20
        ry = y0 + (h - th) // 2
        draw.text((rx, ry), right_text, font=font_small, fill=white)

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

    # ---- TOP BANNER (720x120) ----
    # Prioridad: QR.top_banner (si enable_top_banner) → anuncio por país
    top_source = None
    if getattr(qr, "enable_top_banner", False) and getattr(qr, "top_banner", None):
        top_source = qr.top_banner
    else:
        ad = None
        try:
            ad = get_banner_for_country(country_code, country_name)
        except Exception:
            ad = None
        if ad and getattr(ad, "image", None):
            top_source = ad.image

    top = load_image_or_color(
        top_source,
        fallback_rgba=(255, 255, 255, 255),
        size=(CANVAS_W, TOP_H),
    )
    canvas.paste(top, (0, 0), top)

    # ---- MÁSCARA CENTRAL (720x1150) ----
    central = load_image_or_color(
        getattr(qr, "mask_banner", None),
        fallback_rgba=(235, 235, 235, 255),
        size=(CANVAS_W, CENTRAL_H),
    )
    canvas.paste(central, (0, TOP_H), central)

    # ---- QR (330x330) ----
    qr_img = make_qr(qr.data, size=QR_SIZE)
    qr_x = (CANVAS_W - QR_SIZE) // 2
    qr_y = (CANVAS_H - FOOTER_H) - QR_SIZE
    canvas.paste(qr_img, (qr_x, qr_y), qr_img)

    # ---- FOOTER ----
    draw_footer(canvas, str(qr.id), font_path, valid_until=valid_until)

    # ---- GUARDAR PNG ----
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

    # ---- Estado de validez temporal ----
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
