from fastapi import UploadFile

from app.core.config import settings

# Magic bytes for the formats we accept — checked against actual content,
# never trusted from the client-supplied filename or Content-Type header alone.
_MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",  # WebP: 'RIFF'....'WEBP' — checked more precisely below
}


class InvalidImageError(Exception):
    pass


def _sniff_mime_type(header: bytes) -> str | None:
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    return None


async def validate_image(file: UploadFile) -> bytes:
    """
    Reads the full upload, enforces size limit, and verifies the real file
    content (not just the extension/Content-Type) matches an allowed type.
    Returns the raw bytes for downstream use.
    """
    contents = await file.read()

    if len(contents) > settings.max_image_size_bytes:
        raise InvalidImageError(
            f"Image exceeds the {settings.max_image_size_mb}MB limit."
        )
    if len(contents) == 0:
        raise InvalidImageError("Uploaded file is empty.")

    sniffed = _sniff_mime_type(contents[:16])
    if sniffed is None or sniffed not in settings.allowed_image_types_list:
        raise InvalidImageError(
            "File is not a recognized JPEG, PNG, or WebP image."
        )

    return contents
