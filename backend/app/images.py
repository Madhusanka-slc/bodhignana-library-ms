"""Book cover and member photo pictures: saved as small JPEG files in a folder on the server."""
import base64
import io
import os
import re
import shutil
import time

from fastapi import HTTPException
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError

NAME_RE = re.compile(r"\d+-\d+\.jpg")


def new_name(owner_id: int) -> str:
    """A new file name each time, so browsers show the new picture instead of an old cached one."""
    return f"{owner_id}-{int(time.time() * 1000)}.jpg"


def save_picture(data_url: str, folder: str, owner_id: int, max_size: tuple[int, int]) -> str:
    """Save a picture sent as a data URL; returns the file name."""
    raw = re.sub(r"^data:image/[a-zA-Z+.-]+;base64,", "", data_url or "")
    if not raw or len(raw) > 14_000_000:
        raise HTTPException(400, "Please choose a picture smaller than 10 MB")
    try:
        img = Image.open(io.BytesIO(base64.b64decode(raw)))
        img = ImageOps.exif_transpose(img).convert("RGB")  # phone photos: turn the right way up
    except (ValueError, UnidentifiedImageError, OSError):
        raise HTTPException(400, "This file is not a picture. Please choose a JPG or PNG photo.")
    img.thumbnail(max_size)
    os.makedirs(folder, exist_ok=True)
    name = new_name(owner_id)
    img.save(os.path.join(folder, name), "JPEG", quality=85, optimize=True)
    return name


def copy_picture(folder: str, name: str, owner_id: int) -> str:
    src = os.path.join(folder, name or "")
    if not name or not os.path.exists(src):
        raise HTTPException(400, "There is no picture to copy")
    new = new_name(owner_id)
    shutil.copyfile(src, os.path.join(folder, new))
    return new


def delete_picture(folder: str, name: str):
    if name:
        try:
            os.remove(os.path.join(folder, name))
        except FileNotFoundError:
            pass


def picture_response(folder: str, name: str) -> FileResponse:
    path = os.path.join(folder, name)
    if not NAME_RE.fullmatch(name) or not os.path.exists(path):
        raise HTTPException(404, "No such picture")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=31536000, immutable"})
