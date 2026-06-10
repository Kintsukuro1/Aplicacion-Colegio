import io
import uuid
from datetime import datetime

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.text import get_valid_filename
from PIL import Image, ImageOps
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _resolve_max_upload_size() -> int:
    # 8MB por defecto para fotos moviles.
    return int(getattr(settings, "API_IMAGE_UPLOAD_MAX_BYTES", 8 * 1024 * 1024))


def _validate_image_file(file_obj):
    if not file_obj:
        return False, "Debe enviar un archivo en el campo 'file'."

    if file_obj.size > _resolve_max_upload_size():
        return False, "El archivo excede el tamano maximo permitido."

    content_type = (getattr(file_obj, "content_type", "") or "").lower()
    if content_type not in ALLOWED_IMAGE_MIME_TYPES:
        return False, "Tipo de archivo no permitido. Use JPEG, PNG o WEBP."

    return True, None


def _compress_image(file_obj):
    with Image.open(file_obj) as image:
        image = ImageOps.exif_transpose(image)

        # Mantener transparencia si aplica; JPEG para casos generales.
        has_alpha = image.mode in ("RGBA", "LA")
        target_format = "PNG" if has_alpha else "JPEG"

        if target_format == "JPEG" and image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        # Limita resolucion para controlar payload movil.
        image.thumbnail((1920, 1920), Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        save_kwargs = {"optimize": True}
        if target_format == "JPEG":
            save_kwargs.update({"quality": 80, "progressive": True})

        image.save(buffer, format=target_format, **save_kwargs)
        width, height = image.size

    buffer.seek(0)
    return buffer.getvalue(), target_format, width, height


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser])
def upload_image(request):
    file_obj = request.FILES.get("file")
    is_valid, error = _validate_image_file(file_obj)
    if not is_valid:
        return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

    try:
        compressed_bytes, image_format, width, height = _compress_image(file_obj)
    except Exception:
        return Response({"detail": "No se pudo procesar la imagen."}, status=status.HTTP_400_BAD_REQUEST)

    ext = "jpg" if image_format == "JPEG" else "png"
    base_name = get_valid_filename(file_obj.name.rsplit(".", 1)[0] or "upload")
    date_path = datetime.now().strftime("%Y/%m")
    filename = f"{base_name}-{uuid.uuid4().hex[:10]}.{ext}"
    storage_path = f"uploads/api/{date_path}/{filename}"

    saved_path = default_storage.save(storage_path, ContentFile(compressed_bytes))

    return Response(
        {
            "path": saved_path,
            "url": default_storage.url(saved_path),
            "content_type": "image/jpeg" if image_format == "JPEG" else "image/png",
            "size": len(compressed_bytes),
            "width": width,
            "height": height,
            "storage": default_storage.__class__.__name__,
        },
        status=status.HTTP_201_CREATED,
    )
