import os
import io
import time
import unicodedata
import logging
from typing import Optional, List
from PIL import Image
import pytesseract

from app.services.ocr.base import BaseOCRProvider
from app.services.ocr.models import (
    NormalizedBoundingBox,
    RawOCRToken,
    OCRRecognitionResult,
)

logger = logging.getLogger("metrixa.ocr.tesseract")

class TesseractOCRProvider(BaseOCRProvider):
    """
    Tesseract OCR Provider for Metrixa.
    Safely probes for local Tesseract executable and converts pytesseract output
    into the standard Metrixa OCR contract with normalized coordinates.
    """

    def __init__(self, tesseract_cmd: Optional[str] = None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        else:
            self._probe_tesseract_binary()
        self._cached_version: Optional[str] = None
        self._checked_availability: bool = False
        self._available: bool = False

    @staticmethod
    def _probe_tesseract_binary():
        """
        Probe for Tesseract binary across environments:
        1. Explicit TESSERACT_CMD from settings or environment variable.
        2. System PATH (default on Linux containers where tesseract is in /usr/bin/tesseract).
        3. Local Windows development paths and bundled project binaries.
        """
        # 1. Explicit environment variable or settings
        from app.core.config import settings
        explicit_cmd = settings.TESSERACT_CMD or os.environ.get("TESSERACT_CMD")
        if explicit_cmd and os.path.isfile(explicit_cmd):
            pytesseract.pytesseract.tesseract_cmd = explicit_cmd
            logger.info("Configured Tesseract binary from TESSERACT_CMD: %s", explicit_cmd)
            return

        # 2. System PATH (standard for Linux/Docker)
        try:
            pytesseract.get_tesseract_version()
            return
        except Exception:
            pass

        # 3. Local Windows development fallbacks
        current_file = os.path.abspath(__file__)
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(current_file), "..", "..", ".."))
        candidates = [
            os.path.join(backend_dir, "tesseract_bin", "tesseract.exe"),
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                pytesseract.pytesseract.tesseract_cmd = candidate
                tessdata_dir = os.path.join(os.path.dirname(candidate), "tessdata")
                if os.path.isdir(tessdata_dir) and "TESSDATA_PREFIX" not in os.environ:
                    os.environ["TESSDATA_PREFIX"] = tessdata_dir
                logger.info("Auto-configured Tesseract binary: %s (tessdata: %s)", candidate, tessdata_dir)
                break

    @property
    def name(self) -> str:
        return "Tesseract OCR"

    @property
    def version(self) -> Optional[str]:
        if not self._checked_availability:
            self.is_available()
        return self._cached_version

    def is_available(self) -> bool:
        """
        Check if tesseract executable is installed and runnable on the current environment.
        Caches the result so subsequent checks are instant.
        """
        if self._checked_availability:
            return self._available

        try:
            ver = pytesseract.get_tesseract_version()
            self._cached_version = str(ver)
            self._available = True
            logger.info("Tesseract OCR detected successfully: version %s", self._cached_version)
        except Exception as e:
            self._cached_version = None
            self._available = False
            logger.warning("Tesseract OCR executable is not available on this host: %s", str(e))

        self._checked_availability = True
        return self._available

    def _sanitize_ocr_text(self, text: str) -> str:
        """
        Safe technical cleanup:
        - Normalize unicode to NFKC
        - Strip non-printable/unsafe control characters (except standard space)
        - Clean whitespace
        CRITICAL: Does NOT alter semantic content (e.g. '45O g' is preserved as '45O g').
        """
        normalized = unicodedata.normalize("NFKC", text)
        # Filter out control characters except regular whitespace
        sanitized = "".join(ch for ch in normalized if not unicodedata.category(ch).startswith("C"))
        return sanitized.strip()

    def recognize(self, image_bytes: bytes, **kwargs) -> OCRRecognitionResult:
        """
        Execute OCR using Tesseract engine.
        Returns standardized OCRRecognitionResult. Never raises unhandled exception to the caller.
        """
        start_time = time.perf_counter()

        if not self.is_available():
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return OCRRecognitionResult(
                provider_name=self.name,
                provider_version=None,
                status="PROVIDER_UNAVAILABLE",
                tokens=[],
                raw_text="",
                duration_ms=round(duration_ms, 2),
                error_message="Tesseract executable is not installed or not found. OCR provider unavailable — configure Tesseract OCR.",
            )

    @staticmethod
    def _map_box_back(rot_angle: int, xr: float, yr: float, wr: float, hr: float) -> Tuple[float, float, float, float]:
        """Invert normalized bounding box coordinates back to original unrotated image space."""
        if rot_angle == 0:
            return xr, yr, wr, hr
        elif rot_angle == 90:  # 90 deg clockwise
            return yr, 1.0 - (xr + wr), hr, wr
        elif rot_angle == 180:  # 180 deg
            return 1.0 - (xr + wr), 1.0 - (yr + hr), wr, hr
        elif rot_angle == 270:  # 270 deg clockwise
            return 1.0 - (yr + hr), xr, hr, wr
        raise ValueError(f"Unsupported rotation angle: {rot_angle}")

    @staticmethod
    def _bbox_iou(b1: NormalizedBoundingBox, b2: NormalizedBoundingBox) -> float:
        """Calculate IoU of two normalized bounding boxes."""
        x1 = max(b1.x, b2.x)
        y1 = max(b1.y, b2.y)
        x2 = min(b1.x + b1.width, b2.x + b2.width)
        y2 = min(b1.y + b1.height, b2.y + b2.height)

        inter_w = max(0.0, x2 - x1)
        inter_h = max(0.0, y2 - y1)
        inter_area = inter_w * inter_h
        if inter_area <= 0.0:
            return 0.0

        union_area = (b1.width * b1.height) + (b2.width * b2.height) - inter_area
        return inter_area / union_area if union_area > 0.0 else 0.0

    def recognize(self, image_bytes: bytes, multi_orientation: bool = True, **kwargs) -> OCRRecognitionResult:
        """
        Execute OCR using Tesseract engine.
        Supports multi-orientation token extraction and adaptive resolution scaling
        for curved, rotated, and small-label consumer packaging.
        Returns standardized OCRRecognitionResult. Never raises unhandled exception to the caller.
        """
        start_time = time.perf_counter()

        if not self.is_available():
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return OCRRecognitionResult(
                provider_name=self.name,
                provider_version=None,
                status="PROVIDER_UNAVAILABLE",
                tokens=[],
                raw_text="",
                duration_ms=round(duration_ms, 2),
                error_message="Tesseract executable is not installed or not found. OCR provider unavailable — configure Tesseract OCR.",
            )

        try:
            # Open image with Pillow to determine dimensions
            with Image.open(io.BytesIO(image_bytes)) as pil_img:
                pil_img.load()
                orig_w, orig_h = pil_img.size

                # Adaptive scaling for small packaging crops (< 800px on smallest side)
                min_dim = min(orig_w, orig_h)
                if min_dim < 800:
                    scale = min(3.0, max(2.0, 1000.0 / min_dim))
                    work_img = pil_img.resize((int(orig_w * scale), int(orig_h * scale)), Image.Resampling.BICUBIC)
                else:
                    work_img = pil_img.copy()

            work_w, work_h = work_img.size
            tokens: List[RawOCRToken] = []
            text_chunks: List[str] = []
            token_order = 0
            total_boxes_scanned = 0

            # Scan 0° first, followed by orthogonal angles if multi_orientation is enabled
            rotations = [0, 90, 180, 270] if multi_orientation else [0]

            for rot in rotations:
                if rot == 0:
                    scan_img = work_img
                elif rot == 90:
                    scan_img = work_img.transpose(Image.ROTATE_270)  # 90 deg CW
                elif rot == 180:
                    scan_img = work_img.transpose(Image.ROTATE_180)
                elif rot == 270:
                    scan_img = work_img.transpose(Image.ROTATE_90)  # 270 deg CW

                sw, sh = scan_img.size
                data = pytesseract.image_to_data(scan_img, output_type=pytesseract.Output.DICT)
                n_boxes = len(data.get("text", []))
                total_boxes_scanned += n_boxes

                for i in range(n_boxes):
                    raw_token_text = data["text"][i]
                    clean_text = self._sanitize_ocr_text(raw_token_text)
                    if not clean_text:
                        continue

                    raw_conf = float(data.get("conf", [0])[i])
                    # In secondary rotations, require positive word confidence to prevent orientation noise
                    if rot != 0 and (raw_conf < 30.0 or len(clean_text) < 2):
                        continue

                    normalized_conf = max(0.0, min(1.0, raw_conf / 100.0)) if raw_conf >= 0 else 0.0

                    left_norm = float(data.get("left", [0])[i]) / sw
                    top_norm = float(data.get("top", [0])[i]) / sh
                    width_norm = float(data.get("width", [0])[i]) / sw
                    height_norm = float(data.get("height", [0])[i]) / sh

                    ox, oy, ow, oh = self._map_box_back(rot, left_norm, top_norm, width_norm, height_norm)
                    # Safe clamping within [0, 1]
                    ox = max(0.0, min(1.0, ox))
                    oy = max(0.0, min(1.0, oy))
                    ow = max(0.0, min(1.0 - ox, ow))
                    oh = max(0.0, min(1.0 - oy, oh))

                    bbox = NormalizedBoundingBox(
                        x=round(ox, 6),
                        y=round(oy, 6),
                        width=round(ow, 6),
                        height=round(oh, 6),
                    )

                    # Deduplicate overlapping tokens across rotation passes
                    is_duplicate = False
                    for existing in tokens:
                        if self._bbox_iou(bbox, existing.bounding_box) > 0.40:
                            is_duplicate = True
                            if normalized_conf > existing.confidence + 0.15:
                                existing.confidence = round(normalized_conf, 4)
                                existing.text = clean_text
                            break

                    if not is_duplicate:
                        tokens.append(
                            RawOCRToken(
                                text=clean_text,
                                confidence=round(normalized_conf, 4),
                                bounding_box=bbox,
                                polygon_coords={
                                    "top_left": [bbox.x, bbox.y],
                                    "top_right": [round(bbox.x + bbox.width, 6), bbox.y],
                                    "bottom_right": [round(bbox.x + bbox.width, 6), round(bbox.y + bbox.height, 6)],
                                    "bottom_left": [bbox.x, round(bbox.y + bbox.height, 6)],
                                },
                                token_order=token_order,
                            )
                        )
                        text_chunks.append(clean_text)
                        token_order += 1

            # Fallback for sparse text packaging (e.g. single logo / banner surfaces)
            if len(tokens) < 5:
                d_sparse = pytesseract.image_to_data(work_img, output_type=pytesseract.Output.DICT, config="--psm 11")
                n_sparse = len(d_sparse.get("text", []))
                total_boxes_scanned += n_sparse
                for i in range(n_sparse):
                    raw_token_text = d_sparse["text"][i]
                    clean_text = self._sanitize_ocr_text(raw_token_text)
                    if not clean_text or len(clean_text) < 2:
                        continue
                    raw_conf = float(d_sparse.get("conf", [0])[i])
                    if raw_conf < 30.0:
                        continue
                    normalized_conf = max(0.0, min(1.0, raw_conf / 100.0))

                    left_norm = max(0.0, min(1.0, float(d_sparse.get("left", [0])[i]) / work_w))
                    top_norm = max(0.0, min(1.0, float(d_sparse.get("top", [0])[i]) / work_h))
                    width_norm = max(0.0, min(1.0 - left_norm, float(d_sparse.get("width", [0])[i]) / work_w))
                    height_norm = max(0.0, min(1.0 - top_norm, float(d_sparse.get("height", [0])[i]) / work_h))

                    bbox = NormalizedBoundingBox(
                        x=round(left_norm, 6),
                        y=round(top_norm, 6),
                        width=round(width_norm, 6),
                        height=round(height_norm, 6),
                    )

                    if not any(self._bbox_iou(bbox, ex.bounding_box) > 0.40 for ex in tokens):
                        tokens.append(
                            RawOCRToken(
                                text=clean_text,
                                confidence=round(normalized_conf, 4),
                                bounding_box=bbox,
                                polygon_coords={
                                    "top_left": [bbox.x, bbox.y],
                                    "top_right": [round(bbox.x + bbox.width, 6), bbox.y],
                                    "bottom_right": [round(bbox.x + bbox.width, 6), round(bbox.y + bbox.height, 6)],
                                    "bottom_left": [bbox.x, round(bbox.y + bbox.height, 6)],
                                },
                                token_order=token_order,
                            )
                        )
                        text_chunks.append(clean_text)
                        token_order += 1

            full_text = " ".join(text_chunks)
            status = "COMPLETED" if tokens else "EMPTY"
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            return OCRRecognitionResult(
                provider_name=self.name,
                provider_version=self.version,
                status=status,
                tokens=tokens,
                raw_text=full_text,
                duration_ms=round(duration_ms, 2),
                metadata={"total_boxes_scanned": total_boxes_scanned},
            )

        except Exception as e:
            logger.error("Tesseract OCR execution failed: %s", str(e), exc_info=True)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return OCRRecognitionResult(
                provider_name=self.name,
                provider_version=self.version,
                status="FAILED",
                tokens=[],
                raw_text="",
                duration_ms=round(duration_ms, 2),
                error_message=f"OCR execution failed: {str(e)}",
            )
