import io
import time
from typing import Optional, List, Dict, Any
from PIL import Image

from app.services.ocr.base import BaseOCRProvider
from app.services.ocr.models import (
    NormalizedBoundingBox,
    RawOCRToken,
    OCRRecognitionResult,
)

# Golden statutory packaging tokens used for deterministic testing and mock OCR
GOLDEN_TEST_TOKENS = [
    {"text": "METRIXA", "conf": 0.98, "bbox": (0.05, 0.08, 0.25, 0.05)},
    {"text": "PREMIUM", "conf": 0.95, "bbox": (0.32, 0.08, 0.20, 0.05)},
    {"text": "GREEN", "conf": 0.96, "bbox": (0.54, 0.08, 0.15, 0.05)},
    {"text": "TEA", "conf": 0.99, "bbox": (0.71, 0.08, 0.12, 0.05)},
    {"text": "Mfd", "conf": 0.92, "bbox": (0.05, 0.20, 0.10, 0.04)},
    {"text": "By:", "conf": 0.94, "bbox": (0.16, 0.20, 0.08, 0.04)},
    {"text": "Metrixa", "conf": 0.97, "bbox": (0.26, 0.20, 0.22, 0.04)},
    {"text": "Foods", "conf": 0.95, "bbox": (0.50, 0.20, 0.16, 0.04)},
    {"text": "Pvt", "conf": 0.93, "bbox": (0.68, 0.20, 0.10, 0.04)},
    {"text": "Ltd,", "conf": 0.91, "bbox": (0.80, 0.20, 0.12, 0.04)},
    {"text": "Plot", "conf": 0.89, "bbox": (0.05, 0.26, 0.12, 0.04)},
    {"text": "42,", "conf": 0.88, "bbox": (0.19, 0.26, 0.10, 0.04)},
    {"text": "Industrial", "conf": 0.90, "bbox": (0.31, 0.26, 0.28, 0.04)},
    {"text": "Area,", "conf": 0.89, "bbox": (0.61, 0.26, 0.16, 0.04)},
    {"text": "New", "conf": 0.92, "bbox": (0.05, 0.32, 0.12, 0.04)},
    {"text": "Delhi", "conf": 0.94, "bbox": (0.19, 0.32, 0.16, 0.04)},
    {"text": "110001", "conf": 0.96, "bbox": (0.37, 0.32, 0.20, 0.04)},
    {"text": "NET", "conf": 0.97, "bbox": (0.05, 0.45, 0.12, 0.05)},
    {"text": "QUANTITY:", "conf": 0.98, "bbox": (0.19, 0.45, 0.30, 0.05)},
    {"text": "500", "conf": 0.99, "bbox": (0.52, 0.45, 0.12, 0.05)},
    {"text": "g", "conf": 0.96, "bbox": (0.66, 0.45, 0.06, 0.05)},
    {"text": "MRP", "conf": 0.98, "bbox": (0.05, 0.55, 0.12, 0.05)},
    {"text": "Rs.", "conf": 0.94, "bbox": (0.19, 0.55, 0.10, 0.05)},
    {"text": "250.00", "conf": 0.97, "bbox": (0.31, 0.55, 0.20, 0.05)},
    {"text": "(INCL.", "conf": 0.92, "bbox": (0.53, 0.55, 0.18, 0.05)},
    {"text": "OF", "conf": 0.90, "bbox": (0.73, 0.55, 0.08, 0.05)},
    {"text": "ALL", "conf": 0.91, "bbox": (0.83, 0.55, 0.10, 0.05)},
    {"text": "TAXES)", "conf": 0.93, "bbox": (0.05, 0.62, 0.20, 0.05)},
    {"text": "MFG", "conf": 0.95, "bbox": (0.05, 0.72, 0.12, 0.04)},
    {"text": "DATE:", "conf": 0.96, "bbox": (0.19, 0.72, 0.16, 0.04)},
    {"text": "01/2026", "conf": 0.97, "bbox": (0.37, 0.72, 0.22, 0.04)},
    {"text": "CUSTOMER", "conf": 0.92, "bbox": (0.05, 0.82, 0.26, 0.04)},
    {"text": "CARE:", "conf": 0.93, "bbox": (0.33, 0.82, 0.16, 0.04)},
    {"text": "1800-111-222", "conf": 0.95, "bbox": (0.51, 0.82, 0.35, 0.04)},
    {"text": "EMAIL:", "conf": 0.94, "bbox": (0.05, 0.88, 0.18, 0.04)},
    {"text": "care@metrixa.example.com", "conf": 0.96, "bbox": (0.25, 0.88, 0.65, 0.04)},
    {"text": "Country", "conf": 0.95, "bbox": (0.05, 0.92, 0.15, 0.04)},
    {"text": "of", "conf": 0.95, "bbox": (0.21, 0.92, 0.06, 0.04)},
    {"text": "Origin:", "conf": 0.96, "bbox": (0.28, 0.92, 0.16, 0.04)},
    {"text": "India", "conf": 0.98, "bbox": (0.45, 0.92, 0.12, 0.04)},
    {"text": "USP:", "conf": 0.94, "bbox": (0.05, 0.96, 0.10, 0.03)},
    {"text": "Rs.", "conf": 0.93, "bbox": (0.16, 0.96, 0.08, 0.03)},
    {"text": "0.50", "conf": 0.95, "bbox": (0.25, 0.96, 0.10, 0.03)},
    {"text": "/", "conf": 0.92, "bbox": (0.36, 0.96, 0.03, 0.03)},
    {"text": "g", "conf": 0.94, "bbox": (0.40, 0.96, 0.05, 0.03)},
]

# Canonical tokens representing Front (Principal Display Panel) declarations
FRONT_PDP_TEST_TOKENS = [
    {"text": "METRIXA", "conf": 0.98, "bbox": (0.05, 0.08, 0.25, 0.05)},
    {"text": "PREMIUM", "conf": 0.95, "bbox": (0.32, 0.08, 0.20, 0.05)},
    {"text": "GREEN", "conf": 0.96, "bbox": (0.54, 0.08, 0.15, 0.05)},
    {"text": "TEA", "conf": 0.99, "bbox": (0.71, 0.08, 0.12, 0.05)},
    {"text": "Generic", "conf": 0.93, "bbox": (0.05, 0.20, 0.15, 0.04)},
    {"text": "Name:", "conf": 0.94, "bbox": (0.22, 0.20, 0.12, 0.04)},
    {"text": "Darjeeling", "conf": 0.95, "bbox": (0.36, 0.20, 0.20, 0.04)},
    {"text": "Green", "conf": 0.96, "bbox": (0.58, 0.20, 0.14, 0.04)},
    {"text": "Tea", "conf": 0.97, "bbox": (0.74, 0.20, 0.10, 0.04)},
    {"text": "NET", "conf": 0.97, "bbox": (0.05, 0.45, 0.12, 0.05)},
    {"text": "QUANTITY:", "conf": 0.98, "bbox": (0.19, 0.45, 0.30, 0.05)},
    {"text": "500", "conf": 0.99, "bbox": (0.52, 0.45, 0.12, 0.05)},
    {"text": "g", "conf": 0.96, "bbox": (0.66, 0.45, 0.06, 0.05)},
    {"text": "MRP", "conf": 0.98, "bbox": (0.05, 0.58, 0.12, 0.05)},
    {"text": "Rs.", "conf": 0.94, "bbox": (0.19, 0.58, 0.10, 0.05)},
    {"text": "250.00", "conf": 0.97, "bbox": (0.31, 0.58, 0.20, 0.05)},
    {"text": "(INCL.", "conf": 0.92, "bbox": (0.53, 0.58, 0.18, 0.05)},
    {"text": "OF", "conf": 0.90, "bbox": (0.73, 0.58, 0.08, 0.05)},
    {"text": "ALL", "conf": 0.91, "bbox": (0.83, 0.58, 0.10, 0.05)},
    {"text": "TAXES)", "conf": 0.93, "bbox": (0.05, 0.65, 0.20, 0.05)},
    {"text": "MFG", "conf": 0.95, "bbox": (0.05, 0.72, 0.12, 0.04)},
    {"text": "DATE:", "conf": 0.96, "bbox": (0.19, 0.72, 0.16, 0.04)},
    {"text": "01/2026", "conf": 0.97, "bbox": (0.37, 0.72, 0.22, 0.04)},
    {"text": "USP:", "conf": 0.94, "bbox": (0.05, 0.80, 0.10, 0.04)},
    {"text": "Rs.", "conf": 0.93, "bbox": (0.16, 0.80, 0.08, 0.04)},
    {"text": "0.50", "conf": 0.95, "bbox": (0.25, 0.80, 0.10, 0.04)},
    {"text": "/", "conf": 0.92, "bbox": (0.36, 0.80, 0.03, 0.04)},
    {"text": "g", "conf": 0.94, "bbox": (0.40, 0.80, 0.05, 0.04)},
    {"text": "CUSTOMER", "conf": 0.92, "bbox": (0.05, 0.88, 0.22, 0.04)},
    {"text": "CARE:", "conf": 0.93, "bbox": (0.29, 0.88, 0.14, 0.04)},
    {"text": "1800-111-222", "conf": 0.95, "bbox": (0.45, 0.88, 0.32, 0.04)},
    {"text": "EMAIL:", "conf": 0.94, "bbox": (0.05, 0.94, 0.16, 0.04)},
    {"text": "care@metrixa.example.com", "conf": 0.96, "bbox": (0.23, 0.94, 0.60, 0.04)},
]

# Canonical tokens representing Back panel statutory declarations
BACK_TEST_TOKENS = [
    {"text": "Mfd", "conf": 0.92, "bbox": (0.05, 0.10, 0.08, 0.04)},
    {"text": "&", "conf": 0.94, "bbox": (0.14, 0.10, 0.04, 0.04)},
    {"text": "Packed", "conf": 0.94, "bbox": (0.19, 0.10, 0.14, 0.04)},
    {"text": "By:", "conf": 0.94, "bbox": (0.34, 0.10, 0.08, 0.04)},
    {"text": "Metrixa", "conf": 0.97, "bbox": (0.44, 0.10, 0.18, 0.04)},
    {"text": "Foods", "conf": 0.95, "bbox": (0.64, 0.10, 0.14, 0.04)},
    {"text": "Pvt", "conf": 0.93, "bbox": (0.05, 0.16, 0.08, 0.04)},
    {"text": "Ltd,", "conf": 0.91, "bbox": (0.14, 0.16, 0.10, 0.04)},
    {"text": "Plot", "conf": 0.89, "bbox": (0.26, 0.16, 0.10, 0.04)},
    {"text": "42,", "conf": 0.88, "bbox": (0.38, 0.16, 0.08, 0.04)},
    {"text": "Industrial", "conf": 0.90, "bbox": (0.48, 0.16, 0.20, 0.04)},
    {"text": "Area,", "conf": 0.89, "bbox": (0.70, 0.16, 0.14, 0.04)},
    {"text": "New", "conf": 0.92, "bbox": (0.05, 0.22, 0.10, 0.04)},
    {"text": "Delhi", "conf": 0.94, "bbox": (0.17, 0.22, 0.14, 0.04)},
    {"text": "110001", "conf": 0.96, "bbox": (0.33, 0.22, 0.16, 0.04)},
    {"text": "MFG", "conf": 0.95, "bbox": (0.05, 0.36, 0.10, 0.04)},
    {"text": "DATE:", "conf": 0.96, "bbox": (0.17, 0.36, 0.14, 0.04)},
    {"text": "01/2026", "conf": 0.97, "bbox": (0.33, 0.36, 0.20, 0.04)},
    {"text": "Batch", "conf": 0.94, "bbox": (0.05, 0.48, 0.12, 0.04)},
    {"text": "No:", "conf": 0.95, "bbox": (0.19, 0.48, 0.08, 0.04)},
    {"text": "BATCH-MET-2026-A1", "conf": 0.97, "bbox": (0.29, 0.48, 0.42, 0.04)},
    {"text": "CUSTOMER", "conf": 0.92, "bbox": (0.05, 0.62, 0.24, 0.04)},
    {"text": "CARE:", "conf": 0.93, "bbox": (0.31, 0.62, 0.14, 0.04)},
    {"text": "1800-111-222", "conf": 0.95, "bbox": (0.47, 0.62, 0.32, 0.04)},
    {"text": "EMAIL:", "conf": 0.94, "bbox": (0.05, 0.70, 0.16, 0.04)},
    {"text": "care@metrixa.example.com", "conf": 0.96, "bbox": (0.23, 0.70, 0.60, 0.04)},
    {"text": "Country", "conf": 0.95, "bbox": (0.05, 0.82, 0.16, 0.04)},
    {"text": "of", "conf": 0.95, "bbox": (0.23, 0.82, 0.06, 0.04)},
    {"text": "Origin:", "conf": 0.96, "bbox": (0.31, 0.82, 0.16, 0.04)},
    {"text": "India", "conf": 0.98, "bbox": (0.49, 0.82, 0.14, 0.04)},
]

class MockDeterministicOCRProvider(BaseOCRProvider):
    """
    Deterministic Local OCR Provider for testing, local CI/CD pipelines,
    and environments where external OCR C++ binaries like Tesseract are absent.
    Produces repeatable normalized tokens with realistic confidences and bounding boxes.
    """

    def __init__(
        self,
        custom_tokens: Optional[List[Dict[str, Any]]] = None,
        simulate_empty: bool = False,
        simulate_failure: bool = False,
    ):
        self._custom_tokens_provided = custom_tokens is not None
        self._tokens_config = custom_tokens if custom_tokens is not None else GOLDEN_TEST_TOKENS
        self.simulate_empty = simulate_empty
        self.simulate_failure = simulate_failure

    @property
    def name(self) -> str:
        return "Mock Deterministic OCR"

    @property
    def version(self) -> Optional[str]:
        return "1.0.0-synthetic"

    def is_available(self) -> bool:
        return True

    def recognize(self, image_bytes: bytes, **kwargs) -> OCRRecognitionResult:
        start_time = time.perf_counter()

        if self.simulate_failure:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return OCRRecognitionResult(
                provider_name=self.name,
                provider_version=self.version,
                status="FAILED",
                tokens=[],
                raw_text="",
                duration_ms=round(duration_ms, 2),
                error_message="Simulated OCR provider failure for testing.",
            )

        # Resolve tokens based on custom config or surface type
        if self._custom_tokens_provided:
            tokens_to_use = self._tokens_config
        else:
            surface_type = str(kwargs.get("surface_type", "")).upper()
            if "FRONT" in surface_type or "PDP" in surface_type:
                tokens_to_use = FRONT_PDP_TEST_TOKENS
            elif "BACK" in surface_type:
                tokens_to_use = BACK_TEST_TOKENS
            else:
                tokens_to_use = self._tokens_config

        if self.simulate_empty or not tokens_to_use:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return OCRRecognitionResult(
                provider_name=self.name,
                provider_version=self.version,
                status="EMPTY",
                tokens=[],
                raw_text="",
                duration_ms=round(duration_ms, 2),
                metadata={"total_tokens": 0},
            )

        tokens: List[RawOCRToken] = []
        text_chunks: List[str] = []

        for idx, item in enumerate(tokens_to_use):
            text = item["text"]
            conf = item.get("conf", 0.95)
            bx, by, bw, bh = item["bbox"]

            bbox = NormalizedBoundingBox(
                x=round(bx, 6),
                y=round(by, 6),
                width=round(bw, 6),
                height=round(bh, 6)
            )

            tokens.append(
                RawOCRToken(
                    text=text,
                    confidence=conf,
                    bounding_box=bbox,
                    polygon_coords={
                        "top_left": [bbox.x, bbox.y],
                        "top_right": [round(bbox.x + bbox.width, 6), bbox.y],
                        "bottom_right": [round(bbox.x + bbox.width, 6), round(bbox.y + bbox.height, 6)],
                        "bottom_left": [bbox.x, round(bbox.y + bbox.height, 6)],
                    },
                    token_order=idx,
                )
            )
            text_chunks.append(text)

        full_text = " ".join(text_chunks)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        return OCRRecognitionResult(
            provider_name=self.name,
            provider_version=self.version,
            status="COMPLETED",
            tokens=tokens,
            raw_text=full_text,
            duration_ms=round(duration_ms, 2),
            metadata={"total_tokens": len(tokens)},
        )
