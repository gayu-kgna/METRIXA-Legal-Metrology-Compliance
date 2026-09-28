import io
import time
import uuid
import hashlib
import logging
from typing import Optional, List, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.inspection import Inspection
from app.models.surface import InspectionSurface
from app.models.ocr_run import OCRRun
from app.models.ocr_region import OCRRegion
from app.services.storage.base import BaseStorageService
from app.services.cv.preprocessing import CVPreprocessingService
from app.services.ocr.base import BaseOCRProvider
from app.services.ocr.tesseract import TesseractOCRProvider
from app.services.ocr.mock_provider import MockDeterministicOCRProvider
from app.services.ocr.models import (
    NormalizedBoundingBox,
    RawOCRToken,
    OCRRecognitionResult,
)

logger = logging.getLogger("metrixa.ocr.service")

class OCRProcessingService:
    """
    Dedicated domain service orchestrating the full Computer Vision and OCR pipeline:
    Image Ingestion / Storage Reference
        ↓
    Integrity Verification (SHA-256 verification)
        ↓
    CV Preprocessing (configurable variant, derivative stored separately)
        ↓
    Modular OCR Recognition (Tesseract / Mock)
        ↓
    Spatial Coordinate Validation (Normalized Bounding Boxes in [0, 1])
        ↓
    Historical Traceability Persistence (OCRRun + OCRRegion)
    """

    def __init__(
        self,
        storage_service: BaseStorageService,
        cv_service: Optional[CVPreprocessingService] = None,
        default_provider: Optional[BaseOCRProvider] = None,
    ):
        self.storage_service = storage_service
        self.cv_service = cv_service or CVPreprocessingService(storage_service=storage_service)
        # Default to Tesseract provider if available, else fallback cleanly
        self.default_provider = default_provider or TesseractOCRProvider()

    def get_provider(self, provider_preference: Optional[str] = None) -> BaseOCRProvider:
        """
        Resolve the requested OCR provider by name or return configured default.
        """
        if not provider_preference:
            return self.default_provider

        pref = provider_preference.lower().strip()
        if "tesseract" in pref:
            return TesseractOCRProvider()
        elif "mock" in pref or "synthetic" in pref or "deterministic" in pref:
            return MockDeterministicOCRProvider()
        else:
            logger.info("Unknown OCR provider '%s' requested, using default provider.", provider_preference)
            return self.default_provider

    def validate_bounding_box(self, bbox: NormalizedBoundingBox) -> NormalizedBoundingBox:
        """
        Ensure bounding box strictly obeys [0, 1] normalized boundaries.
        Clamps slight float deviations safely.
        """
        x = max(0.0, min(1.0, float(bbox.x)))
        y = max(0.0, min(1.0, float(bbox.y)))
        max_w = max(0.0, 1.0 - x)
        max_h = max(0.0, 1.0 - y)
        w = max(0.0, min(max_w, float(bbox.width)))
        h = max(0.0, min(max_h, float(bbox.height)))
        return NormalizedBoundingBox(x=round(x, 6), y=round(y, 6), width=round(w, 6), height=round(h, 6))

    async def execute_ocr_pipeline(
        self,
        db: AsyncSession,
        inspection: Inspection,
        surface: InspectionSurface,
        preprocessing_variant: str = "original",
        provider_name: Optional[str] = None,
        provider_instance: Optional[BaseOCRProvider] = None,
    ) -> OCRRun:
        """
        Run OCR on an inspection package surface image:
        1. Retrieves original image bytes from storage.
        2. Validates original SHA-256 against database record.
        3. Executes CV preprocessing variant and stores derivative.
        4. Invokes OCR provider.
        5. Validates and normalizes bounding boxes.
        6. Persists new immutable OCRRun and OCRRegion entities.
        """
        pipeline_start = time.perf_counter()
        logger.info(
            "Starting OCR pipeline: inspection_id=%s, surface_id=%s, variant=%s, provider=%s",
            inspection.id, surface.id, preprocessing_variant, provider_name
        )

        # 1. Retrieve original image bytes
        if not await self.storage_service.exists(surface.image_storage_path):
            raise FileNotFoundError(f"Original image file not found at storage path: {surface.image_storage_path}")

        original_bytes = await self.storage_service.retrieve(surface.image_storage_path)

        # 2. Verify image integrity
        current_sha256 = hashlib.sha256(original_bytes).hexdigest()
        if current_sha256 != surface.sha256_hash:
            raise ValueError(
                f"Image integrity violation: SHA-256 mismatch for surface {surface.id}. "
                f"Expected {surface.sha256_hash}, calculated {current_sha256}."
            )

        # 3. CV Preprocessing
        prep_start = time.perf_counter()
        prep_variant = preprocessing_variant.strip().lower() or "original"
        processed_image_ref: Optional[str] = None
        target_bytes_for_ocr = original_bytes
        prep_metadata: Dict[str, Any] = {}

        if prep_variant != "original":
            prep_result = await self.cv_service.generate_and_store_variant(
                inspection_id=inspection.id,
                surface_id=surface.id,
                original_bytes=original_bytes,
                variant=prep_variant,
            )
            processed_image_ref = prep_result.storage_reference
            target_bytes_for_ocr = prep_result.processed_bytes
            prep_metadata = {
                "variant_name": prep_result.variant_name,
                "operations_applied": prep_result.operations_applied,
                "source_dimensions": prep_result.source_dimensions,
                "output_dimensions": prep_result.output_dimensions,
                "metadata": prep_result.metadata,
            }
            prep_duration_ms = prep_result.duration_ms
        else:
            prep_duration_ms = (time.perf_counter() - prep_start) * 1000.0
            prep_metadata = {"variant_name": "original", "operations_applied": []}

        # 4. Invoke OCR Provider
        ocr_provider = provider_instance or self.get_provider(provider_name)
        ocr_start = time.perf_counter()
        surface_type_str = surface.surface_type.value if hasattr(surface.surface_type, "value") else str(surface.surface_type)
        ocr_result: OCRRecognitionResult = ocr_provider.recognize(
            target_bytes_for_ocr,
            surface_type=surface_type_str,
        )
        ocr_duration_ms = (time.perf_counter() - ocr_start) * 1000.0

        total_duration_ms = (time.perf_counter() - pipeline_start) * 1000.0

        # Count detected metrics
        total_chars = sum(len(t.text) for t in ocr_result.tokens)
        total_regions = len(ocr_result.tokens)

        # 5. Create immutable OCRRun record
        ocr_run = OCRRun(
            id=uuid.uuid4(),
            inspection_id=inspection.id,
            surface_id=surface.id,
            provider_name=ocr_result.provider_name,
            provider_version=ocr_result.provider_version,
            preprocessing_variant=prep_variant,
            processed_image_ref=processed_image_ref,
            status=ocr_result.status,
            total_regions_detected=total_regions,
            total_characters_detected=total_chars,
            preprocessing_duration_ms=round(prep_duration_ms, 2),
            ocr_duration_ms=round(ocr_duration_ms, 2),
            total_duration_ms=round(total_duration_ms, 2),
            error_message=ocr_result.error_message,
            metadata_json={
                "raw_text": ocr_result.raw_text,
                "preprocessing": prep_metadata,
                "provider_metadata": ocr_result.metadata,
            },
        )
        db.add(ocr_run)

        # 6. Persist OCRRegion tokens with validated normalized bounding boxes
        persisted_regions: List[OCRRegion] = []
        for token in ocr_result.tokens:
            valid_bbox = self.validate_bounding_box(token.bounding_box)
            region = OCRRegion(
                id=uuid.uuid4(),
                surface_id=surface.id,
                ocr_run_id=ocr_run.id,
                raw_text=token.text,
                confidence=round(token.confidence, 4),
                bounding_box=valid_bbox.to_dict(),
                polygon_coords=token.polygon_coords or {
                    "top_left": [valid_bbox.x, valid_bbox.y],
                    "top_right": [round(valid_bbox.x + valid_bbox.width, 6), valid_bbox.y],
                    "bottom_right": [round(valid_bbox.x + valid_bbox.width, 6), round(valid_bbox.y + valid_bbox.height, 6)],
                    "bottom_left": [valid_bbox.x, round(valid_bbox.y + valid_bbox.height, 6)],
                },
                token_order=token.token_order,
            )
            db.add(region)
            persisted_regions.append(region)

        await db.commit()
        await db.refresh(ocr_run)

        logger.info(
            "OCR pipeline finished: run_id=%s, status=%s, regions=%d, chars=%d, total_time=%.2fms",
            ocr_run.id, ocr_run.status, total_regions, total_chars, total_duration_ms
        )
        return ocr_run

    async def get_ocr_runs_for_surface(
        self,
        db: AsyncSession,
        surface_id: uuid.UUID
    ) -> List[OCRRun]:
        """
        Retrieve all historical OCR runs for a package surface image,
        ordered chronologically.
        """
        query = (
            select(OCRRun)
            .where(OCRRun.surface_id == surface_id)
            .order_by(OCRRun.executed_at.desc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())
