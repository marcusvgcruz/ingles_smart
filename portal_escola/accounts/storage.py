"""Storages de mídia: AWS S3 ou Cloudinary em produção, disco local em desenvolvimento."""

from django.conf import settings
from django.core.files.storage import default_storage


def _s3_enabled() -> bool:
    return getattr(settings, "USE_S3", False)


def _cloudinary_enabled() -> bool:
    return getattr(settings, "USE_CLOUDINARY", False)


def raw_file_storage():
    """PDF, áudio e outros arquivos não-imagem (tipo raw no Cloudinary ou default no S3/Local)."""
    if _cloudinary_enabled() and not _s3_enabled():
        from cloudinary_storage.storage import RawMediaCloudinaryStorage

        return RawMediaCloudinaryStorage()
    return default_storage


def is_external_file(field_file) -> bool:
    if not field_file:
        return False
    name = (field_file.name or "").lower()
    return name.startswith("http://") or name.startswith("https://") or "cloudinary.com" in name or "amazonaws.com" in name

is_cloudinary_file = is_external_file

