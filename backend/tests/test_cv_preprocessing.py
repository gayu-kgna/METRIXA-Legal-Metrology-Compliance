import io
import uuid
import hashlib
import pytest
from PIL import Image, ImageDraw

from app.services.cv.models import PreprocessingOp, PRESET_VARIANTS, PreprocessingResult
from app.services.cv.preprocessing import CVPreprocessingService
from app.services.storage.local import LocalStorageService

def create_synthetic_package_image(width=400, height=300) -> bytes:
    """Create a synthetic package image with crisp text and high contrast."""
    img = Image.new("RGB", (width, height), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    # Draw simulated label border
    draw.rectangle([20, 20, width - 20, height - 20], outline=(40, 40, 40), width=3)
    # Draw simulated commodity text
    draw.text((40, 50), "BRAND: METRIXA ORGANIC TEA", fill=(10, 10, 10))
    draw.text((40, 90), "NET QUANTITY: 500 g", fill=(10, 10, 10))
    draw.text((40, 130), "MRP: Rs. 250.00 (INCL. OF ALL TAXES)", fill=(10, 10, 10))
    draw.text((40, 170), "MFG DATE: 01/2026", fill=(10, 10, 10))
    draw.text((40, 210), "CONSUMER CARE: 1800-111-222", fill=(10, 10, 10))
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def test_preprocessing_service_init():
    service = CVPreprocessingService()
    assert service.storage_service is None
    preset_names = list(PRESET_VARIANTS.keys())
    assert "original" in preset_names
    assert "grayscale" in preset_names
    assert "clahe" in preset_names
    assert "adaptive_threshold" in preset_names
    assert "otsu_threshold" in preset_names
    assert "deskew_upscale" in preset_names

def test_original_image_bytes_immutability():
    service = CVPreprocessingService()
    orig_bytes = create_synthetic_package_image(300, 300)
    orig_sha = hashlib.sha256(orig_bytes).hexdigest()

    # Run multiple variants
    for variant in ["original", "grayscale", "contrast", "clahe", "adaptive_threshold", "otsu_threshold", "deskew_upscale"]:
        result = service.process_image(orig_bytes, variant=variant)
        assert result.processed_bytes is not None
        assert len(result.processed_bytes) > 0
        # Verify input bytes were untouched
        assert hashlib.sha256(orig_bytes).hexdigest() == orig_sha

def test_variant_operations_metadata():
    service = CVPreprocessingService()
    orig_bytes = create_synthetic_package_image(200, 150)
    
    res_clahe = service.process_image(orig_bytes, variant="clahe")
    assert res_clahe.variant_name == "clahe"
    assert "clahe" in res_clahe.operations_applied
    assert res_clahe.source_dimensions == (200, 150)
    assert res_clahe.output_dimensions == (200, 150)
    assert res_clahe.duration_ms >= 0.0

    res_upscale = service.process_image(orig_bytes, variant="deskew_upscale")
    assert res_upscale.source_dimensions == (200, 150)
    # Upscale 2x should double output dimensions
    assert res_upscale.output_dimensions == (400, 300)

@pytest.mark.asyncio
async def test_generate_and_store_variant(tmp_path):
    storage = LocalStorageService(storage_root=tmp_path)
    service = CVPreprocessingService(storage_service=storage)

    inspection_id = uuid.uuid4()
    surface_id = uuid.uuid4()
    orig_bytes = create_synthetic_package_image(250, 200)

    # Store original first
    orig_ref = storage.build_inspection_path_reference(inspection_id, "original", f"{surface_id}.png")
    await storage.store(orig_ref, orig_bytes)

    # Generate and store processed variant
    res = await service.generate_and_store_variant(
        inspection_id=inspection_id,
        surface_id=surface_id,
        original_bytes=orig_bytes,
        variant="adaptive_threshold"
    )

    assert res.storage_reference is not None
    assert f"inspections/{inspection_id}/processed/{surface_id}_adaptive_threshold.png" in res.storage_reference
    assert await storage.exists(res.storage_reference)

    # Verify original file in storage is still byte-identical
    stored_orig = await storage.retrieve(orig_ref)
    assert hashlib.sha256(stored_orig).hexdigest() == hashlib.sha256(orig_bytes).hexdigest()

def test_invalid_image_and_variant():
    service = CVPreprocessingService()
    with pytest.raises(ValueError, match="Unknown preprocessing variant"):
        service.resolve_operations("unsupported_super_filter")

    with pytest.raises(ValueError, match="Failed to decode image bytes"):
        service.process_image(b"not_an_image_bytes")
