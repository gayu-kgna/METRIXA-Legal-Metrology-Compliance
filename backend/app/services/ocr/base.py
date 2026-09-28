from abc import ABC, abstractmethod
from typing import Optional
from app.services.ocr.models import OCRRecognitionResult

class BaseOCRProvider(ABC):
    """
    Abstract interface for OCR providers in Metrixa.
    Decouples Metrixa from specific OCR engines (Tesseract, PaddleOCR, EasyOCR, etc.),
    ensuring OCR engines can be swapped or augmented without modifying the core system.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name, e.g. 'Tesseract OCR'."""
        pass

    @property
    @abstractmethod
    def version(self) -> Optional[str]:
        """Provider executable/library version string."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the OCR engine and its dependencies are present on the host."""
        pass

    @abstractmethod
    def recognize(self, image_bytes: bytes, **kwargs) -> OCRRecognitionResult:
        """
        Perform optical character recognition on the given image bytes.
        Returns a standardized OCRRecognitionResult.
        Must never raise unhandled crashes if provider executable is missing.
        """
        pass
