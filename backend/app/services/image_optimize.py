import io

from PIL import Image

MAX_DIMENSION = 1600  # longest side, in pixels
JPEG_QUALITY = 82


def optimize_image(raw_bytes: bytes) -> tuple[bytes, str]:
    """
    Resizes to a capped longest-side dimension and re-encodes as JPEG to keep
    R2 storage costs down. Only called for signed-in users' saved images —
    anonymous uploads never reach this function (see extract.py).

    Returns (optimized_bytes, content_type).
    """
    with Image.open(io.BytesIO(raw_bytes)) as img:
        img = img.convert("RGB")  # drops alpha/CMYK edge cases, normalizes for JPEG
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

        out = io.BytesIO()
        img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return out.getvalue(), "image/jpeg"
