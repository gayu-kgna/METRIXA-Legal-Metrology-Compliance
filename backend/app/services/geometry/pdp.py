import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.inspection import Inspection
from app.models.surface import InspectionSurface
from app.models.observation import Observation
from app.models.pdp_geometry import PDPGeometry
from app.models.enums import SurfaceType
from app.services.geometry.models import CalibrationInput, DeclarationSpatialPlacement

logger = logging.getLogger("metrixa.geometry.pdp")

class PDPGeometryService:
    """
    Dedicated service for Principal Display Panel (PDP) geometry analysis.
    Measures display area in image pixels, calculates text height geometry,
    maps statutory declaration placement, and applies physical calibration when available.
    
    CRITICAL ARCHITECTURAL SAFEGUARD:
    Does NOT evaluate legal compliance or font-size sufficiency.
    Physical dimensions are populated ONLY when authentic calibration data exists;
    otherwise physical measurements remain explicitly None/uncalibrated with zero fabrication.
    """

    def _determine_quadrant(self, bbox: Dict[str, float]) -> str:
        """Determine spatial quadrant or zone based on normalized center coordinates."""
        cx = bbox.get("x", 0.0) + (bbox.get("width", 0.0) / 2.0)
        cy = bbox.get("y", 0.0) + (bbox.get("height", 0.0) / 2.0)

        vert = "TOP" if cy < 0.33 else ("BOTTOM" if cy > 0.66 else "CENTER")
        horiz = "LEFT" if cx < 0.33 else ("RIGHT" if cx > 0.66 else "CENTER")

        if vert == "CENTER" and horiz == "CENTER":
            return "CENTER"
        elif vert == "CENTER":
            return f"CENTER_{horiz}"
        elif horiz == "CENTER":
            return f"{vert}_CENTER"
        return f"{vert}_{horiz}"

    async def analyze_pdp_geometry(
        self,
        db: AsyncSession,
        inspection: Inspection,
        surface: InspectionSurface,
        calibration: Optional[CalibrationInput] = None,
    ) -> PDPGeometry:
        """
        Analyze the geometry of a package surface image.
        Treats FRONT_PDP as primary candidate. If non-PDP surface, records that PDP is unavailable.
        """
        img_w = surface.image_width or 1
        img_h = surface.image_height or 1

        is_pdp = (surface.surface_type == SurfaceType.FRONT_PDP)
        detection_method = "CANONICAL_FRONT_PDP_SURFACE" if is_pdp else "NON_PDP_SURFACE"

        pdp_bbox = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
        pdp_pixel_w = float(img_w)
        pdp_pixel_h = float(img_h)
        pdp_pixel_area = pdp_pixel_w * pdp_pixel_h

        # Calibration resolution
        scale_px_per_mm: Optional[float] = None
        calib_source: Optional[str] = None
        has_calib = False
        phys_w_mm: Optional[float] = None
        phys_h_mm: Optional[float] = None
        phys_area_cm2: Optional[float] = None
        uncertainty_dict: Dict[str, Any] = {}

        if calibration and calibration.scale_px_per_mm and calibration.scale_px_per_mm > 0:
            scale_px_per_mm = calibration.scale_px_per_mm
            calib_source = calibration.calibration_source or "MANUAL_SCALE"
            has_calib = True
        elif calibration and calibration.reference_dimension_mm and calibration.reference_dimension_px:
            if calibration.reference_dimension_mm > 0 and calibration.reference_dimension_px > 0:
                scale_px_per_mm = round(calibration.reference_dimension_px / calibration.reference_dimension_mm, 4)
                calib_source = calibration.calibration_source or "REFERENCE_MARKER"
                has_calib = True

        if has_calib and scale_px_per_mm:
            phys_w_mm = round(pdp_pixel_w / scale_px_per_mm, 2)
            phys_h_mm = round(pdp_pixel_h / scale_px_per_mm, 2)
            # 1 sq cm = 100 sq mm
            phys_area_cm2 = round((phys_w_mm * phys_h_mm) / 100.0, 2)
            uncertainty_dict = {
                "calibration_state": "CALIBRATED",
                "scale_px_per_mm": scale_px_per_mm,
                "uncertainty_percent": 2.5,
                "notes": f"Calibrated via {calib_source}. Physical dimensions are computed.",
            }
        else:
            uncertainty_dict = {
                "calibration_state": "UNCALIBRATED",
                "notes": "No physical calibration provided. Physical dimensions remain uncalibrated/None with zero fabrication.",
            }

        # Analyze existing statutory declarations/observations placement on this surface
        obs_query = select(Observation).where(
            Observation.inspection_id == inspection.id,
            Observation.surface_id == surface.id,
            Observation.is_latest == True,
        )
        obs_res = await db.execute(obs_query)
        observations = obs_res.scalars().all()

        declarations_geom_list: List[Dict[str, Any]] = []
        for obs in observations:
            bbox = obs.bounding_box or {}
            box_h = float(bbox.get("height", 0.0))
            text_h_px = round(box_h * img_h, 2)
            phys_text_h_mm = round(text_h_px / scale_px_per_mm, 2) if has_calib and scale_px_per_mm else None
            quadrant = self._determine_quadrant(bbox)

            placement = DeclarationSpatialPlacement(
                field_type=obs.field_type.value,
                quadrant=quadrant,
                bounding_box=bbox,
                estimated_text_height_px=text_h_px,
                estimated_physical_text_height_mm=phys_text_h_mm,
                relative_height_to_pdp=round(box_h, 6),
                uncertainty={
                    "is_calibrated": has_calib,
                    "text_height_metric": "BOUNDING_BOX_PIXEL_HEIGHT",
                },
            )
            declarations_geom_list.append(placement.model_dump())

        status = "COMPLETED" if (is_pdp and has_calib) else ("UNCALIBRATED" if is_pdp else "NOT_PDP_SURFACE")

        geometry_run = PDPGeometry(
            id=uuid.uuid4(),
            inspection_id=inspection.id,
            surface_id=surface.id,
            surface_type=surface.surface_type,
            is_pdp_candidate=is_pdp,
            image_width=img_w,
            image_height=img_h,
            pdp_bounding_box=pdp_bbox,
            pdp_pixel_width=round(pdp_pixel_w, 2),
            pdp_pixel_height=round(pdp_pixel_h, 2),
            pdp_pixel_area=round(pdp_pixel_area, 2),
            has_calibration=has_calib,
            calibration_source=calib_source,
            scale_px_per_mm=scale_px_per_mm,
            estimated_physical_width_mm=phys_w_mm,
            estimated_physical_height_mm=phys_h_mm,
            estimated_physical_area_sq_cm=phys_area_cm2,
            measurement_uncertainty=uncertainty_dict,
            declarations_geometry={"declarations": declarations_geom_list, "count": len(declarations_geom_list)},
            detection_method=detection_method,
            confidence=1.0 if is_pdp else 0.5,
            status=status,
            analyzed_at=datetime.now(timezone.utc),
            metadata_json={"surface_name": surface.surface_type.value},
        )
        db.add(geometry_run)
        await db.commit()
        await db.refresh(geometry_run)

        logger.info(
            "PDP Geometry analysis completed: id=%s, is_pdp=%s, status=%s, area_px=%.1f, area_cm2=%s",
            geometry_run.id, is_pdp, status, pdp_pixel_area, phys_area_cm2
        )
        return geometry_run

    async def get_pdp_geometry_for_surface(
        self,
        db: AsyncSession,
        surface_id: uuid.UUID,
    ) -> List[PDPGeometry]:
        """Retrieve historical PDP geometry analyses for a package surface."""
        query = (
            select(PDPGeometry)
            .where(PDPGeometry.surface_id == surface_id)
            .order_by(PDPGeometry.analyzed_at.desc())
        )
        res = await db.execute(query)
        return list(res.scalars().all())
