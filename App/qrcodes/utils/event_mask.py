# qrcodes/utils/event_mask.py
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from io import BytesIO
from PIL import Image

def event_mask_path(event_id: int) -> str:
    return f"ads/masks/event_{event_id}.png"

def save_event_mask(event_id: int, uploaded_image_file) -> str:
    uploaded_image_file.seek(0)
    with Image.open(uploaded_image_file) as im:
        im = im.convert("RGBA").resize((720, 1150), Image.LANCZOS)
        buf = BytesIO()
        im.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        content = ContentFile(buf.read())
    dest_path = event_mask_path(event_id)
    try:
        if default_storage.exists(dest_path):
            default_storage.delete(dest_path)
    except Exception:
        pass
    default_storage.save(dest_path, content)
    return dest_path
