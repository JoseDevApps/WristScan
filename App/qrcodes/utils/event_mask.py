# qrcodes/utils/event_mask.py
# from django.core.files.base import ContentFile
# from django.core.files.storage import default_storage
# from io import BytesIO
# from PIL import Image

# def event_mask_path(event_id: int) -> str:
#     return f"ads/masks/event_{event_id}.png"

# def save_event_mask(event_id: int, uploaded_image_file) -> str:
#     uploaded_image_file.seek(0)
#     with Image.open(uploaded_image_file) as im:
#         im = im.convert("RGBA").resize((720, 1150), Image.LANCZOS)
#         buf = BytesIO()
#         im.save(buf, format="PNG", optimize=True)
#         buf.seek(0)
#         content = ContentFile(buf.read())
#     dest_path = event_mask_path(event_id)
#     try:
#         if default_storage.exists(dest_path):
#             default_storage.delete(dest_path)
#     except Exception:
#         pass
#     default_storage.save(dest_path, content)
#     return dest_path

# qrcodes/utils/event_mask.py
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image
import io

MASK_W, MASK_H = 720, 1150

def save_event_mask(event_id: int, uploaded_file) -> str:
    """
    Normaliza y guarda la máscara del evento.
    Devuelve el 'name' relativo que puedes asignar a ImageField (p.ej. 'ads/masks/12/mask.png').
    """
    # Lee bytes
    data = uploaded_file.read()
    im = Image.open(io.BytesIO(data)).convert("RGBA")
    im = im.resize((MASK_W, MASK_H), Image.LANCZOS)

    # Re-empacar a PNG
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    buf.seek(0)

    # Ruta relativa para storage
    rel_dir = f"ads/masks/{event_id}"
    rel_name = f"{rel_dir}/mask.png"

    # Asegura directorio y guarda
    if default_storage.exists(rel_name):
        default_storage.delete(rel_name)
    default_storage.save(rel_name, ContentFile(buf.getvalue()))

    return rel_name  # ← esto es lo que asignas a ImageField.name
