"""Storages de mídia: Cloudinary em produção, disco local em desenvolvimento."""

from django.conf import settings
from django.core.files.storage import FileSystemStorage, default_storage


def _cloudinary_enabled() -> bool:
    return getattr(settings, "USE_CLOUDINARY", False)


def raw_file_storage():
    """PDF, áudio e outros arquivos não-imagem (tipo raw no Cloudinary)."""
    if _cloudinary_enabled():
        from cloudinary_storage.storage import RawMediaCloudinaryStorage

        return RawMediaCloudinaryStorage()
    return default_storage


def is_cloudinary_file(field_file) -> bool:
    if not field_file:
        return False
    name = (field_file.name or "").lower()
    return name.startswith("http://") or name.startswith("https://") or "cloudinary.com" in name
