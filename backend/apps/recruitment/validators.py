from pathlib import Path

from django.conf import settings
from rest_framework import serializers

from .choices import ApplicationDocumentType

DOCUMENT_EXTENSIONS = {
    ApplicationDocumentType.CV: {".pdf", ".doc", ".docx"},
    ApplicationDocumentType.COVER_LETTER: {".pdf", ".doc", ".docx"},
    ApplicationDocumentType.PERSONAL_PHOTO: {".jpg", ".jpeg", ".png"},
    ApplicationDocumentType.OTHER: {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"},
}

DOCUMENT_MIME_TYPES = {
    ApplicationDocumentType.CV: {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
    ApplicationDocumentType.COVER_LETTER: {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
    ApplicationDocumentType.PERSONAL_PHOTO: {
        "image/jpeg",
        "image/png",
    },
    ApplicationDocumentType.OTHER: {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg",
        "image/png",
    },
}

DOCUMENT_MAX_SIZE_SETTINGS = {
    ApplicationDocumentType.CV: "RECRUITMENT_MAX_UPLOAD_SIZE_MB",
    ApplicationDocumentType.COVER_LETTER: "RECRUITMENT_MAX_UPLOAD_SIZE_MB",
    ApplicationDocumentType.PERSONAL_PHOTO: "RECRUITMENT_PHOTO_MAX_UPLOAD_SIZE_MB",
    ApplicationDocumentType.OTHER: "RECRUITMENT_MAX_UPLOAD_SIZE_MB",
}

FILE_SIGNATURES = {
    ".pdf": (b"%PDF",),
    ".doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    ".docx": (b"PK",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
}


def validate_application_file(uploaded_file, document_type: str) -> None:
    max_size_setting = DOCUMENT_MAX_SIZE_SETTINGS.get(
        document_type,
        "RECRUITMENT_MAX_UPLOAD_SIZE_MB",
    )
    max_size_mb = getattr(settings, max_size_setting, 5)
    max_size = max_size_mb * 1024 * 1024
    if not uploaded_file or not uploaded_file.name:
        raise serializers.ValidationError("Fichier obligatoire.")

    if len(uploaded_file.name) > 255:
        raise serializers.ValidationError("Nom de fichier trop long.")

    extension = Path(uploaded_file.name).suffix.lower()
    allowed_extensions = DOCUMENT_EXTENSIONS.get(document_type, set())
    allowed_mime_types = DOCUMENT_MIME_TYPES.get(document_type, set())
    content_type = getattr(uploaded_file, "content_type", "")

    if extension not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise serializers.ValidationError(
            f"Format non autorisé. Utilisez {allowed}."
        )

    if content_type not in allowed_mime_types:
        raise serializers.ValidationError("Type de fichier non autorisé.")

    if uploaded_file.size > max_size:
        raise serializers.ValidationError(
            f"Fichier trop volumineux. Taille maximale: {max_size_mb} Mo."
        )

    if not _has_allowed_signature(uploaded_file, extension):
        raise serializers.ValidationError("Le contenu du fichier ne correspond pas au format annoncé.")


def _has_allowed_signature(uploaded_file, extension: str) -> bool:
    signatures = FILE_SIGNATURES.get(extension)
    if not signatures:
        return True

    try:
        position = uploaded_file.tell()
    except (AttributeError, OSError):
        position = 0
    try:
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        header = uploaded_file.read(16)
    finally:
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(position)

    return any(header.startswith(signature) for signature in signatures)
