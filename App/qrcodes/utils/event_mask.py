

# # qrcodes/utils/event_mask.py
# from pathlib import Path
# from django.core.files.storage import default_storage
# from PIL import Image, ImageOps

# def event_mask_path(event_id: int, filename: str = "mask.png") -> str:
#     return f"ads/masks/{event_id}/{filename}"



# def save_event_mask(event_id: int, uploaded_file) -> str:
#     """
#     Guarda la máscara del evento normalizada a 720x1150 (portrait).
#     Si viene en horizontal (p.ej. 1150x720), la rota automáticamente.
#     Devuelve la ruta relativa (para asignar a QR.mask_banner).
#     """
#     # Abrir imagen del upload
#     with Image.open(uploaded_file) as im:
#         im = im.convert("RGBA")

#         # Autocorrección de orientación si viene apaisada (ancho > alto)
#         if im.width > im.height:
#             im = im.transpose(Image.Transpose.ROTATE_90)

#         # Ajuste tipo "cover" a 720×1150
#         target_size = (720, 1150)
#         im = ImageOps.fit(im, target_size, method=Image.Resampling.LANCZOS, bleed=0.0, centering=(0.5, 0.5))

#         # Guardar en storage
#         rel_path = event_mask_path(event_id, "mask.png")
#         # Guardamos como PNG optimizado
#         from io import BytesIO
#         buf = BytesIO()
#         im.save(buf, format="PNG", optimize=True)
#         buf.seek(0)

#         # Escribir en default_storage
#         if default_storage.exists(rel_path):
#             default_storage.delete(rel_path)
#         with default_storage.open(rel_path, "wb") as dest:
#             dest.write(buf.read())

#         return rel_path


# qrcodes/utils/event_mask.py
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

CANVAS_W, CENTRAL_H = 720, 1150
MASK_NAME_FMT = "ads/masks/{event_id}/mask.png"

def save_event_mask(event_id: int, file_obj) -> str:
    """
    Normaliza la máscara a 720x1150 RGBA y la guarda en default_storage.
    Devuelve el 'name' relativo para asignarlo a ImageField (string).
    """
    # 1) Normaliza tamaño
    with Image.open(file_obj) as im:
        im = ImageOps.fit(im.convert("RGBA"), (CANVAS_W, CENTRAL_H), method=Image.LANCZOS)

        buf = BytesIO()
        im.save(buf, format="PNG")
        buf.seek(0)

    # 2) Guarda en storage
    name = MASK_NAME_FMT.format(event_id=event_id)  # p.ej. ads/masks/12/mask.png
    try:
        if default_storage.exists(name):
            default_storage.delete(name)
    except Exception:
        pass

    default_storage.save(name, ContentFile(buf.read()))
    return name