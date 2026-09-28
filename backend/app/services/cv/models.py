from enum import Enum
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

class PreprocessingOp(str, Enum):
    GRAYSCALE = "grayscale"
    CONTRAST_ENHANCEMENT = "contrast_enhancement"
    CLAHE = "clahe"
    NOISE_REDUCTION = "noise_reduction"
    ADAPTIVE_THRESHOLD = "adaptive_threshold"
    OTSU_THRESHOLD = "otsu_threshold"
    DESKEW = "deskew"
    UPSCALE = "upscale"

PRESET_VARIANTS: Dict[str, List[PreprocessingOp]] = {
    "original": [],
    "grayscale": [PreprocessingOp.GRAYSCALE],
    "contrast": [PreprocessingOp.GRAYSCALE, PreprocessingOp.CONTRAST_ENHANCEMENT],
    "clahe": [PreprocessingOp.GRAYSCALE, PreprocessingOp.CLAHE],
    "adaptive_threshold": [
        PreprocessingOp.GRAYSCALE,
        PreprocessingOp.NOISE_REDUCTION,
        PreprocessingOp.ADAPTIVE_THRESHOLD,
    ],
    "otsu_threshold": [
        PreprocessingOp.GRAYSCALE,
        PreprocessingOp.NOISE_REDUCTION,
        PreprocessingOp.OTSU_THRESHOLD,
    ],
    "deskew_upscale": [
        PreprocessingOp.GRAYSCALE,
        PreprocessingOp.DESKEW,
        PreprocessingOp.UPSCALE,
    ],
}

@dataclass
class PreprocessingResult:
    variant_name: str
    operations_applied: List[str]
    source_dimensions: Tuple[int, int]  # (width, height)
    output_dimensions: Tuple[int, int]  # (width, height)
    processed_bytes: bytes
    duration_ms: float
    storage_reference: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
