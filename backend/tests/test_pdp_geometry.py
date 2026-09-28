import uuid
import pytest
from app.models.inspection import Inspection
from app.models.surface import InspectionSurface
from app.models.observation import Observation
from app.models.enums import SurfaceType, FieldType, ObservationStatus
from app.services.geometry.pdp import PDPGeometryService
from app.services.geometry.models import CalibrationInput

@pytest.mark.asyncio
async def test_pdp_geometry_surface_selection_and_uncalibrated(db_session, test_inspector):
    service = PDPGeometryService()

    # Create test inspection
    ins = Inspection(
        id=uuid.uuid4(),
        inspection_number=f"GEO-{uuid.uuid4().hex[:6]}",
        inspector_id=test_inspector.id,
        retail_outlet_name="Geometry Test Store",
    )
    db_session.add(ins)

    # 1. Non-PDP surface (BACK)
    back_surface = InspectionSurface(
        id=uuid.uuid4(),
        inspection_id=ins.id,
        surface_type=SurfaceType.BACK,
        image_storage_path="inspections/test/original/back.png",
        sha256_hash="dummy_sha",
        image_width=800,
        image_height=600,
    )
    db_session.add(back_surface)
    await db_session.commit()

    geom_back = await service.analyze_pdp_geometry(db_session, ins, back_surface)
    assert geom_back.is_pdp_candidate is False
    assert geom_back.status == "NOT_PDP_SURFACE"
    assert geom_back.estimated_physical_area_sq_cm is None

    # 2. Candidate PDP surface (FRONT_PDP) without calibration
    pdp_surface = InspectionSurface(
        id=uuid.uuid4(),
        inspection_id=ins.id,
        surface_type=SurfaceType.FRONT_PDP,
        image_storage_path="inspections/test/original/front.png",
        sha256_hash="dummy_sha2",
        image_width=1000,
        image_height=800,
    )
    db_session.add(pdp_surface)
    await db_session.commit()

    geom_pdp = await service.analyze_pdp_geometry(db_session, ins, pdp_surface)
    assert geom_pdp.is_pdp_candidate is True
    assert geom_pdp.pdp_pixel_width == 1000.0
    assert geom_pdp.pdp_pixel_height == 800.0
    assert geom_pdp.pdp_pixel_area == 800000.0
    assert geom_pdp.has_calibration is False
    # CRITICAL: Without calibration, physical dimensions MUST be None (zero fabrication)
    assert geom_pdp.estimated_physical_width_mm is None
    assert geom_pdp.estimated_physical_height_mm is None
    assert geom_pdp.estimated_physical_area_sq_cm is None
    assert geom_pdp.status == "UNCALIBRATED"
    assert "UNCALIBRATED" in geom_pdp.measurement_uncertainty.get("calibration_state", "")

@pytest.mark.asyncio
async def test_pdp_geometry_with_calibration_and_text_geometry(db_session, test_inspector):
    service = PDPGeometryService()

    ins = Inspection(
        id=uuid.uuid4(),
        inspection_number=f"GEO-CAL-{uuid.uuid4().hex[:6]}",
        inspector_id=test_inspector.id,
        retail_outlet_name="Calibrated Geometry Store",
    )
    db_session.add(ins)

    surface = InspectionSurface(
        id=uuid.uuid4(),
        inspection_id=ins.id,
        surface_type=SurfaceType.FRONT_PDP,
        image_storage_path="inspections/test/original/calib.png",
        sha256_hash="dummy_sha3",
        image_width=1000,
        image_height=800,
    )
    db_session.add(surface)

    # Add sample observation on this surface
    obs = Observation(
        id=uuid.uuid4(),
        inspection_id=ins.id,
        surface_id=surface.id,
        field_type=FieldType.NET_QUANTITY,
        raw_value="Net Qty: 500 g",
        normalized_value={"value": 500, "unit": "g"},
        confidence=0.98,
        status=ObservationStatus.OBSERVED,
        bounding_box={"x": 0.05, "y": 0.75, "width": 0.30, "height": 0.05},
        is_latest=True,
    )
    db_session.add(obs)
    await db_session.commit()

    # Scale: 10 pixels per mm (so 1000 px = 100 mm, 800 px = 80 mm)
    calib = CalibrationInput(
        scale_px_per_mm=10.0,
        calibration_source="REFERENCE_MARKER",
    )

    geom = await service.analyze_pdp_geometry(db_session, ins, surface, calibration=calib)
    assert geom.is_pdp_candidate is True
    assert geom.has_calibration is True
    assert geom.status == "COMPLETED"
    assert geom.estimated_physical_width_mm == 100.0  # 1000 / 10
    assert geom.estimated_physical_height_mm == 80.0   # 800 / 10
    assert geom.estimated_physical_area_sq_cm == 80.0  # (100 * 80) / 100

    # Verify declaration text geometry
    decl_list = geom.declarations_geometry.get("declarations", [])
    assert len(decl_list) >= 1
    decl = decl_list[0]
    assert decl["field_type"] == "NET_QUANTITY"
    # Text height in pixels: 0.05 * 800 = 40.0 px
    assert decl["estimated_text_height_px"] == 40.0
    # Physical text height: 40.0 / 10 = 4.0 mm
    assert decl["estimated_physical_text_height_mm"] == 4.0
    # Quadrant: y=0.75 (>0.66), x=0.05 (<0.33) -> BOTTOM_LEFT
    assert decl["quadrant"] == "BOTTOM_LEFT"
