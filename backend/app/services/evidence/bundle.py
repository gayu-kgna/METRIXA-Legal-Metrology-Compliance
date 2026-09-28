import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.models.inspection import Inspection
from app.models.surface import InspectionSurface
from app.models.ocr_run import OCRRun
from app.models.observation import Observation
from app.models.pdp_geometry import PDPGeometry
from app.models.rule_evaluation import RuleEvaluation
from app.models.audit_log import AuditLog
from app.services.evidence.models import (
    EvidenceManifest,
    IntegrityManifest,
    IntegrityItem,
)
from app.services.evidence.integrity import calculate_canonical_json_sha256

class EvidenceBundleBuilder:
    """
    Assembles a complete, immutable, structured EvidenceManifest
    from Metrixa database models and perception artifacts.
    """

    @classmethod
    def build_manifest(
        cls,
        inspection: Inspection,
        surfaces: List[InspectionSurface],
        ocr_runs: List[OCRRun],
        observations: List[Observation],
        geometries: List[PDPGeometry],
        evaluations: List[RuleEvaluation],
        audit_logs: List[AuditLog],
        evaluation_run_id: Optional[uuid.UUID] = None,
        bundle_id: Optional[str] = None,
        application_version: str = "1.0.0",
    ) -> EvidenceManifest:
        b_id = bundle_id or str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Inspection data
        inspection_data = {
            "id": str(inspection.id),
            "inspection_number": inspection.inspection_number,
            "overall_status": inspection.overall_status.value if hasattr(inspection.overall_status, "value") else str(inspection.overall_status),
            "retail_outlet_name": inspection.retail_outlet_name,
            "retail_outlet_address": inspection.retail_outlet_address,
            "geo_coordinates": inspection.geo_coordinates or {},
            "initiated_at": inspection.initiated_at.isoformat() if inspection.initiated_at else None,
            "completed_at": inspection.completed_at.isoformat() if inspection.completed_at else None,
        }

        # 2. Product data
        product_data = None
        if inspection.product:
            product_data = {
                "id": str(inspection.product.id),
                "brand_name": inspection.product.brand_name,
                "product_name": inspection.product.product_name,
                "gtin_barcode": inspection.product.gtin_barcode,
                "category": inspection.product.category,
                "commodity_type": inspection.product.commodity_type,
                "manufacturer_claimed": inspection.product.manufacturer_claimed,
            }

        # 3. Images / Surfaces
        images_data = []
        integrity_items = []
        for s in surfaces:
            s_dict = {
                "surface_id": str(s.id),
                "surface_type": s.surface_type.value if hasattr(s.surface_type, "value") else str(s.surface_type),
                "storage_reference": s.image_storage_path,
                "sha256_hash": s.sha256_hash,
                "image_width": s.image_width,
                "image_height": s.image_height,
                "file_size_bytes": s.file_size_bytes,
                "mime_type": s.mime_type,
                "captured_at": s.captured_at.isoformat() if s.captured_at else None,
            }
            images_data.append(s_dict)
            integrity_items.append(
                IntegrityItem(
                    item_id=str(s.id),
                    item_type="ORIGINAL_IMAGE",
                    sha256_hash=s.sha256_hash,
                    description=f"Original capture for surface {s_dict['surface_type']}"
                )
            )

        # 4. OCR Runs & Regions
        ocr_data = []
        for r in ocr_runs:
            regions_summary = []
            if hasattr(r, "regions") and r.regions:
                for reg in r.regions:
                    regions_summary.append({
                        "id": str(reg.id),
                        "raw_text": reg.raw_text,
                        "confidence": float(reg.confidence),
                        "bounding_box": reg.bounding_box,
                        "token_order": reg.token_order,
                    })
            r_dict = {
                "ocr_run_id": str(r.id),
                "surface_id": str(r.surface_id),
                "provider_name": r.provider_name,
                "provider_version": r.provider_version,
                "preprocessing_variant": r.preprocessing_variant,
                "status": r.status,
                "total_regions": r.total_regions_detected,
                "total_duration_ms": r.total_duration_ms,
                "executed_at": r.executed_at.isoformat() if r.executed_at else None,
                "regions": regions_summary,
            }
            ocr_data.append(r_dict)

        # 5. Observations
        obs_data = []
        for o in observations:
            ft_val = o.field_type.value if hasattr(o.field_type, "value") else str(o.field_type)
            conf_val = float(o.confidence)
            o_dict = {
                "id": str(o.id),
                "observation_id": str(o.id),
                "surface_id": str(o.surface_id) if o.surface_id else None,
                "ocr_region_id": str(o.ocr_region_id) if o.ocr_region_id else None,
                "entity_run_id": str(o.entity_run_id) if o.entity_run_id else None,
                "field_type": ft_val,
                "field_name": ft_val,
                "raw_value": o.raw_value,
                "raw_text_extracted": o.raw_value,
                "normalized_value": o.normalized_value or {},
                "confidence": conf_val,
                "confidence_score": conf_val,
                "status": o.status.value if hasattr(o.status, "value") else str(o.status),
                "revision": o.revision,
                "is_latest": o.is_latest,
                "bounding_box": o.bounding_box or {},
                "source": o.source.value if hasattr(o.source, "value") else str(o.source),
                "observed_at": o.observed_at.isoformat() if o.observed_at else None,
            }
            obs_data.append(o_dict)

        # 6. Geometries
        geom_data = []
        for g in geometries:
            g_dict = {
                "id": str(g.id),
                "geometry_id": str(g.id),
                "surface_id": str(g.surface_id),
                "surface_type": g.surface_type.value if hasattr(g.surface_type, "value") else str(g.surface_type),
                "is_pdp_candidate": g.is_pdp_candidate,
                "image_width": g.image_width,
                "image_height": g.image_height,
                "pdp_pixel_width": g.pdp_pixel_width,
                "pdp_pixel_height": g.pdp_pixel_height,
                "pdp_pixel_area": g.pdp_pixel_area,
                "pdp_area_px2": g.pdp_pixel_area,
                "has_calibration": g.has_calibration,
                "is_calibrated": g.has_calibration,
                "scale_px_per_mm": g.scale_px_per_mm,
                "estimated_physical_width_mm": g.estimated_physical_width_mm,
                "estimated_physical_height_mm": g.estimated_physical_height_mm,
                "estimated_physical_area_sq_cm": g.estimated_physical_area_sq_cm,
                "status": g.status,
                "analyzed_at": g.analyzed_at.isoformat() if g.analyzed_at else None,
            }
            geom_data.append(g_dict)

        # 7. Rule Evaluations
        eval_data = []
        rule_versions = {}
        for ev in evaluations:
            r_code = ev.rule_code or (ev.rule_definition.rule_code if ev.rule_definition else "UNKNOWN_RULE")
            r_ver = ev.rule_version or (ev.rule_definition.version if ev.rule_definition else "1.0")
            rule_versions[r_code] = r_ver

            ev_dict = {
                "id": str(ev.id),
                "evaluation_id": str(ev.id),
                "rule_code": r_code,
                "rule_title": ev.rule_definition.title if ev.rule_definition else r_code,
                "rule_version": r_ver,
                "statutory_citation": ev.statutory_citation,
                "outcome": ev.outcome.value if hasattr(ev.outcome, "value") else str(ev.outcome),
                "legal_rationale": ev.legal_rationale,
                "applicability_result": ev.applicability_result or {},
                "evidence_references": ev.evidence_references or {},
                "evaluated_at": ev.evaluated_at.isoformat() if ev.evaluated_at else None,
            }
            eval_data.append(ev_dict)

        # 8. Audit Logs
        audit_data = []
        for a in audit_logs:
            a_dict = {
                "log_id": str(a.id),
                "action": a.action,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "justification": a.justification,
                "performed_at": a.performed_at.isoformat() if a.performed_at else None,
            }
            audit_data.append(a_dict)

        manifest = EvidenceManifest(
            bundle_id=b_id,
            inspection_id=str(inspection.id),
            evaluation_run_id=str(evaluation_run_id) if evaluation_run_id else None,
            created_at=now_iso,
            application_version=application_version,
            parser_version="ENTITY-PARSER-v1",
            normalizer_version="NORMALIZER-v1",
            ocr_provider="Modular OCR Engine",
            inspection=inspection_data,
            product=product_data,
            images=images_data,
            ocr_runs=ocr_data,
            observations=obs_data,
            geometry=geom_data,
            rule_evaluations=eval_data,
            audit_logs=audit_data,
            integrity=IntegrityManifest(items=integrity_items),
        )

        return manifest
