import re
import secrets
from pathlib import Path

MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_NAME_RE = re.compile(r"^[0-9a-f]{32}\.(?:png|jpg|gif|webp)$")
IMAGE_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def image_extension(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def save_image(data: bytes, media_dir: str) -> str:
    extension = image_extension(data)
    if extension is None:
        raise ValueError("Разрешены только PNG, JPEG, WebP и GIF")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Размер изображения не должен превышать 5 МБ")
    path = Path(media_dir)
    path.mkdir(parents=True, exist_ok=True)
    filename = f"{secrets.token_hex(16)}.{extension}"
    (path / filename).write_bytes(data)
    return filename
