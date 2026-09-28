import io
import time
import uuid
import hashlib
import logging
from typing import Union, List, Optional, Tuple, Dict, Any
import numpy as np
import cv2
from PIL import Image

from app.services.storage.base import BaseStorageService
from app.services.cv.models import PreprocessingOp, PRESET_VARIANTS, PreprocessingResult

logger = logging.getLogger("metrixa.cv.preprocessing")

class CVPreprocessingService:
    """
    Modular Computer Vision preprocessing service for Legal Metrology package inspection.
    Transforms raw package surface imagery into high-clarity derivatives optimized for OCR.
    
    Guarantees:
    1. The original image bytes remain 100% byte-for-byte immutable.
    2. All generated derivatives are saved separately under the inspection's processed/ directory.
    3. Operation metrics and metadata are accurately captured.
    """

    def __init__(self, storage_service: Optional[BaseStorageService] = None):
        self.storage_service = storage_service

    def resolve_operations(self, variant: Union[str, List[Union[str, PreprocessingOp]]]) -> Tuple[str, List[PreprocessingOp]]:
        """
        Resolve variant name or custom list of operations into a canonical variant name and op list.
        """
        if isinstance(variant, str):
            variant_key = variant.lower().strip()
            if variant_key in PRESET_VARIANTS:
                return variant_key, PRESET_VARIANTS[variant_key]
            # Check if it's a single operation name
            try:
                op = PreprocessingOp(variant_key)
                return variant_key, [op]
            except ValueError:
                raise ValueError(
                    f"Unknown preprocessing variant '{variant}'. "
                    f"Available presets: {list(PRESET_VARIANTS.keys())}, "
                    f"or individual operations: {[op.value for op in PreprocessingOp]}"
                )
        elif isinstance(variant, list):
            resolved_ops: List[PreprocessingOp] = []
            for op_item in variant:
                if isinstance(op_item, PreprocessingOp):
                    resolved_ops.append(op_item)
                elif isinstance(op_item, str):
                    resolved_ops.append(PreprocessingOp(op_item.lower().strip()))
                else:
                    raise ValueError(f"Invalid operation specification: {op_item}")
            variant_name = "_".join(op.value for op in resolved_ops) or "original"
            return variant_name, resolved_ops
        else:
            raise ValueError(f"Invalid variant format: {type(variant)}")

    def _deskew_image(self, img: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Detect text skew angle and rotate to align horizontally.
        Returns: (deskewed_image, detected_angle)
        """
        gray = img if len(img.shape) == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Invert colors so text is foreground (white)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 10:
            return img, 0.0

        rect = cv2.minAreaRect(coords)
        angle = rect[-1]

        # Determine skew angle in range [-45, 45]
        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle
        else:
            angle = -angle

        # If skew is negligible or too extreme (e.g. false orientation), don't rotate
        if abs(angle) < 0.5 or abs(angle) > 40.0:
            return img, 0.0

        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        # Fill border with white / light background
        border_val = (255, 255, 255) if len(img.shape) == 3 else 255
        rotated = cv2.warpAffine(
            img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=border_val
        )
        return rotated, float(angle)

    def process_image(
        self,
        image_bytes: bytes,
        variant: Union[str, List[Union[str, PreprocessingOp]]] = "original"
    ) -> PreprocessingResult:
        """
        Execute configured preprocessing pipeline on an image in-memory.
        Ensures original image bytes are not modified.
        """
        start_time = time.perf_counter()
        
        # Verify original bytes integrity snapshot
        orig_sha256 = hashlib.sha256(image_bytes).hexdigest()

        variant_name, ops = self.resolve_operations(variant)
        applied_ops_record: List[str] = []
        op_metadata: Dict[str, Any] = {}

        # Decode image using OpenCV
        np_arr = np.frombuffer(image_bytes, np.uint8)
        cv_img = cv2.imdecode(np_arr, cv2.IMREAD_UNCHANGED)
        if cv_img is None:
            raise ValueError("Failed to decode image bytes into OpenCV matrix.")

        src_h, src_w = cv_img.shape[:2]
        current_img = cv_img.copy()

        # Execute operations in order
        for op in ops:
            if op == PreprocessingOp.GRAYSCALE:
                if len(current_img.shape) == 3:
                    if current_img.shape[2] == 4:
                        current_img = cv2.cvtColor(current_img, cv2.COLOR_BGRA2GRAY)
                    else:
                        current_img = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
                applied_ops_record.append("grayscale")

            elif op == PreprocessingOp.CONTRAST_ENHANCEMENT:
                if len(current_img.shape) == 3:
                    current_img = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
                    applied_ops_record.append("grayscale_conversion")
                current_img = cv2.equalizeHist(current_img)
                applied_ops_record.append("contrast_enhancement")

            elif op == PreprocessingOp.CLAHE:
                if len(current_img.shape) == 3:
                    current_img = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
                    applied_ops_record.append("grayscale_conversion")
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                current_img = clahe.apply(current_img)
                applied_ops_record.append("clahe")

            elif op == PreprocessingOp.NOISE_REDUCTION:
                if len(current_img.shape) == 3:
                    current_img = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
                    applied_ops_record.append("grayscale_conversion")
                current_img = cv2.bilateralFilter(current_img, 9, 75, 75)
                applied_ops_record.append("noise_reduction")

            elif op == PreprocessingOp.ADAPTIVE_THRESHOLD:
                if len(current_img.shape) == 3:
                    current_img = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
                    applied_ops_record.append("grayscale_conversion")
                current_img = cv2.adaptiveThreshold(
                    current_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
                )
                applied_ops_record.append("adaptive_threshold")

            elif op == PreprocessingOp.OTSU_THRESHOLD:
                if len(current_img.shape) == 3:
                    current_img = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
                    applied_ops_record.append("grayscale_conversion")
                _, current_img = cv2.threshold(
                    current_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                )
                applied_ops_record.append("otsu_threshold")

            elif op == PreprocessingOp.DESKEW:
                current_img, detected_angle = self._deskew_image(current_img)
                op_metadata["deskew_angle_degrees"] = detected_angle
                applied_ops_record.append(f"deskew({detected_angle:.2f}deg)")

            elif op == PreprocessingOp.UPSCALE:
                current_img = cv2.resize(
                    current_img, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC
                )
                applied_ops_record.append("upscale_2x")

        # Encode processed image to PNG
        encode_success, encoded_buf = cv2.imencode(".png", current_img)
        if not encode_success:
            raise ValueError("Failed to encode processed image to PNG format.")
        processed_bytes = encoded_buf.tobytes()

        # Verify original bytes remain 100% untouched
        post_sha256 = hashlib.sha256(image_bytes).hexdigest()
        assert orig_sha256 == post_sha256, "CRITICAL ERROR: Original image bytes were modified during preprocessing!"

        out_h, out_w = current_img.shape[:2]
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        return PreprocessingResult(
            variant_name=variant_name,
            operations_applied=applied_ops_record,
            source_dimensions=(src_w, src_h),
            output_dimensions=(out_w, out_h),
            processed_bytes=processed_bytes,
            duration_ms=round(duration_ms, 2),
            metadata=op_metadata,
        )

    async def generate_and_store_variant(
        self,
        inspection_id: uuid.UUID,
        surface_id: uuid.UUID,
        original_bytes: bytes,
        variant: Union[str, List[Union[str, PreprocessingOp]]] = "original"
    ) -> PreprocessingResult:
        """
        Process the image and store the processed derivative under
        storage/inspections/{inspection_id}/processed/{surface_id}_{variant}.png.
        """
        if self.storage_service is None:
            raise RuntimeError("Storage service is required to store processed derivatives.")

        # Compute variant result
        result = self.process_image(original_bytes, variant=variant)

        # Build secure storage reference under 'processed' subfolder
        target_filename = f"{surface_id}_{result.variant_name}.png"
        storage_ref = self.storage_service.build_inspection_path_reference(
            inspection_id=inspection_id,
            subfolder="processed",
            filename=target_filename
        )

        persisted_ref = await self.storage_service.store(storage_ref, result.processed_bytes)
        result.storage_reference = persisted_ref
        logger.info(
            "Processed derivative stored: variant=%s, ref=%s, duration=%.2fms",
            result.variant_name, persisted_ref, result.duration_ms
        )
        return result
