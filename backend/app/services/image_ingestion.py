import io
import os
import uuid
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any
from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.inspection import Inspection
from app.models.surface import InspectionSurface
from app.models.enums import SurfaceType
from app.services.storage.base import BaseStorageService
from app.schemas.surface import ImageUploadResponse

logger = logging.getLogger("metrixa.ingestion")

class ImageIngestionService:
    """
    Dedicated domain service for validating, hashing, storing,
    and indexing packaged commodity package images.
    Preserves exact original image bytes and enforces security boundaries.
    """

    def __init__(self, storage_service: BaseStorageService):
        self.storage_service = storage_service

    def validate_image_content(self, data: bytes) -> Tuple[str, str, int, int]:
        """
        Validate image content using Pillow.
        Returns: (detected_format, mime_type, width, height)
        Raises ValueError for invalid, corrupted, or unsupported images.
        """
        if not data or len(data) == 0:
            raise ValueError("Uploaded image file is empty (0 bytes).")

        max_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
        if len(data) > max_bytes:
            raise ValueError(
                f"Image file size ({len(data) / (1024*1024):.2f}MB) exceeds "
                f"maximum allowable limit of {settings.MAX_IMAGE_SIZE_MB}MB."
            )

        # Magic bytes / file signature validation
        is_jpeg = data.startswith(b"\xFF\xD8\xFF")
        is_png = data.startswith(b"\x89PNG\r\n\x1a\n")
        is_webp = data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP"
        if not (is_jpeg or is_png or is_webp):
            raise ValueError("Corrupted or invalid image file signature (magic bytes mismatch).")

        try:
            # First pass: verify structural integrity
            bio = io.BytesIO(data)
            with Image.open(bio) as probe_img:
                probe_img.verify()
                raw_format = probe_img.format
        except (UnidentifiedImageError, OSError, SyntaxError) as e:
            logger.warning("Image verification failed: %s", str(e))
            raise ValueError("Corrupted or invalid image file content.") from e

        if not raw_format:
            raise ValueError("Could not determine image format from file header.")

        detected_format = raw_format.upper()
        if detected_format not in [f.upper() for f in settings.ALLOWED_IMAGE_FORMATS]:
            raise ValueError(
                f"Unsupported image format '{detected_format}'. "
                f"Allowed formats: {settings.ALLOWED_IMAGE_FORMATS}"
            )

        # Second pass: re-open to extract dimensions (verify closes the file/descriptor)
        bio.seek(0)
        with Image.open(bio) as img:
            width, height = img.size

        if width < settings.MIN_IMAGE_DIMENSION or height < settings.MIN_IMAGE_DIMENSION:
            raise ValueError(
                f"Image dimensions ({width}x{height}) are smaller than "
                f"minimum required ({settings.MIN_IMAGE_DIMENSION}x{settings.MIN_IMAGE_DIMENSION}px)."
            )

        if width > settings.MAX_IMAGE_DIMENSION or height > settings.MAX_IMAGE_DIMENSION:
            raise ValueError(
                f"Image dimensions ({width}x{height}) exceed "
                f"maximum allowed ({settings.MAX_IMAGE_DIMENSION}x{settings.MAX_IMAGE_DIMENSION}px)."
            )

        # Canonical MIME mapping
        mime_map = {
            "JPEG": "image/jpeg",
            "JPG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp",
        }
        mime_type = mime_map.get(detected_format, "application/octet-stream")

        return detected_format, mime_type, width, height

    def _sanitize_filename(self, filename: Optional[str], detected_format: str) -> str:
        """
        Sanitize user-provided filename to prevent path traversal
        and ensure extension matches the true detected format.
        """
        ext_map = {
            "JPEG": ".jpg",
            "JPG": ".jpg",
            "PNG": ".png",
            "WEBP": ".webp",
        }
        target_ext = ext_map.get(detected_format, ".bin")

        if not filename:
            return f"package_surface{target_ext}"

        # Strip any directory path components
        base = os.path.basename(filename.replace("\\", "/"))
        # Remove null bytes or dangerous tokens
        cleaned = base.replace("\0", "").strip()
        name, _ = os.path.splitext(cleaned)
        safe_name = "".join(c for c in name if c.isalnum() or c in ("-", "_")).strip() or "surface"
        return f"{safe_name}{target_ext}"

    async def ingest_image(
        self,
        db: AsyncSession,
        inspection: Inspection,
        surface_type: SurfaceType,
        content_bytes: bytes,
        original_filename: Optional[str] = None,
    ) -> ImageUploadResponse:
        """
        Full manual image ingestion pipeline:
        1. Validates content, formats, dimensions, and size.
        2. Calculates SHA-256 on exact original bytes.
        3. Generates safe application-controlled ID and storage reference.
        4. Stores original bytes without modification.
        5. Checks for duplicate content without rejecting legitimate duplicates.
        6. Persists metadata to database.
        """
        logger.info(
            "Ingestion requested: inspection_id=%s, surface=%s, size=%d bytes",
            inspection.id, surface_type.value, len(content_bytes)
        )

        # 1. Content validation
        detected_format, mime_type, width, height = self.validate_image_content(content_bytes)
        logger.info(
            "Validation successful: format=%s, mime=%s, dimensions=%dx%d",
            detected_format, mime_type, width, height
        )

        # 2. Cryptographic SHA-256 calculation
        sha256 = hashlib.sha256(content_bytes).hexdigest()
        logger.info("Calculated SHA-256 hash: %s", sha256)

        # 3. Identifiers and sanitized path construction
        image_id = uuid.uuid4()
        safe_filename = self._sanitize_filename(original_filename, detected_format)
        _, ext = os.path.splitext(safe_filename)
        storage_filename = f"{image_id}{ext}"
        storage_ref = self.storage_service.build_inspection_path_reference(
            inspection_id=inspection.id,
            subfolder="original",
            filename=storage_filename
        )

        # 4. Store original bytes unchanged
        persisted_ref = await self.storage_service.store(storage_ref, content_bytes)
        logger.info("Image stored at reference: %s", persisted_ref)

        # 5. Duplicate content detection (checks across database)
        dup_query = select(InspectionSurface).where(InspectionSurface.sha256_hash == sha256)
        dup_result = await db.execute(dup_query)
        existing_dup = dup_result.scalars().first()

        is_duplicate = existing_dup is not None
        duplicate_of_id = existing_dup.id if existing_dup else None

        if is_duplicate:
            logger.info(
                "Duplicate content identified: sha256=%s, original_surface_id=%s",
                sha256, duplicate_of_id
            )

        # 6. Database entity persistence
        now = datetime.now(timezone.utc)
        surface = InspectionSurface(
            id=image_id,
            inspection_id=inspection.id,
            surface_type=surface_type,
            image_storage_path=persisted_ref,
            sha256_hash=sha256,
            image_width=width,
            image_height=height,
            file_size_bytes=len(content_bytes),
            original_filename=safe_filename,
            mime_type=mime_type,
            detected_format=detected_format,
            quality_metrics={
                "ingestion_stage": "MANUAL_UPLOAD",
                "is_duplicate_content": is_duplicate,
                "duplicate_of_surface_id": str(duplicate_of_id) if duplicate_of_id else None,
            },
            captured_at=now,
        )
        db.add(surface)
        await db.commit()
        await db.refresh(surface)
        logger.info("Surface metadata persisted: surface_id=%s", surface.id)

        return ImageUploadResponse(
            id=surface.id,
            inspection_id=surface.inspection_id,
            surface_type=surface.surface_type,
            original_filename=surface.original_filename,
            mime_type=surface.mime_type,
            detected_format=surface.detected_format,
            file_size_bytes=surface.file_size_bytes,
            image_width=surface.image_width,
            image_height=surface.image_height,
            sha256_hash=surface.sha256_hash,
            storage_reference=surface.image_storage_path,
            is_duplicate=is_duplicate,
            duplicate_of_surface_id=duplicate_of_id,
            captured_at=surface.captured_at,
            quality_metrics=surface.quality_metrics,
        )
