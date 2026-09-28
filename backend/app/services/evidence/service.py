import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.inspection import Inspection
from app.models.surface import InspectionSurface
from app.models.ocr_run import OCRRun
from app.models.ocr_region import OCRRegion
from app.models.adjudication import OCRAdjudication
from app.models.observation import Observation
from app.models.pdp_geometry import PDPGeometry
from app.models.rule_evaluation import RuleEvaluation
from app.models.audit_log import AuditLog
from app.models.evidence import EvidenceSnapshot
from app.models.enums import ObservationSource, CorrectionType
from app.services.evidence.models import (
    EvidenceCategory,
    EvidenceTraceNode,
    EvidenceTraceGraph,
    EvidenceManifest,
)
from app.services.evidence.bundle import EvidenceBundleBuilder
from app.services.evidence.integrity import (
    calculate_canonical_json_sha256,
    verify_canonical_json_sha256,
)

class EvidenceService:
    """
    Core Evidence Management Service for Metrixa.
    Provides evidence graph assembly, reference validation,
    cryptographic SHA-256 integrity sealing, and immutable point-in-time snapshots.
    """

    async def load_inspection_dataset(
        self,
        db: AsyncSession,
        inspection_id: uuid.UUID,
        evaluation_run_id: Optional[uuid.UUID] = None,
    ) -> Tuple[Inspection, List[InspectionSurface], List[OCRRun], List[Observation], List[PDPGeometry], List[RuleEvaluation], List[AuditLog]]:
        """Load complete inspection perception, observation, geometry, rule, and audit records."""
        # Load inspection with product and inspector
        stmt_insp = (
            select(Inspection)
            .options(
                selectinload(Inspection.product),
                selectinload(Inspection.inspector),
            )
            .where(Inspection.id == inspection_id)
        )
        insp_res = await db.execute(stmt_insp)
        inspection = insp_res.scalar_one_or_none()
        if not inspection:
            raise ValueError(f"Inspection {inspection_id} not found")

        # Load surfaces
        stmt_surf = select(InspectionSurface).where(InspectionSurface.inspection_id == inspection_id)
        surf_res = await db.execute(stmt_surf)
        surfaces = list(surf_res.scalars().all())

        # Load OCR runs with regions
        stmt_ocr = (
            select(OCRRun)
            .options(selectinload(OCRRun.regions))
            .where(OCRRun.inspection_id == inspection_id)
            .order_by(OCRRun.executed_at.desc())
        )
        ocr_res = await db.execute(stmt_ocr)
        ocr_runs = list(ocr_res.scalars().all())

        # Load observations (latest active revisions only)
        stmt_obs = (
            select(Observation)
            .where(
                Observation.inspection_id == inspection_id,
                Observation.is_latest == True,
            )
            .order_by(Observation.created_at.asc())
        )
        obs_res = await db.execute(stmt_obs)
        observations = list(obs_res.scalars().all())

        # Load geometries
        stmt_geom = (
            select(PDPGeometry)
            .where(PDPGeometry.inspection_id == inspection_id)
            .order_by(PDPGeometry.analyzed_at.desc())
        )
        geom_res = await db.execute(stmt_geom)
        geometries = list(geom_res.scalars().all())

        # Resolve target evaluation run if not provided
        target_eval_run_id = evaluation_run_id
        if not target_eval_run_id:
            latest_run_stmt = (
                select(RuleEvaluation.evaluation_run_id)
                .where(RuleEvaluation.inspection_id == inspection_id)
                .order_by(RuleEvaluation.evaluated_at.desc())
                .limit(1)
            )
            latest_run_res = await db.execute(latest_run_stmt)
            target_eval_run_id = latest_run_res.scalar_one_or_none()

        # Load rule evaluations (isolated to target run)
        stmt_eval = (
            select(RuleEvaluation)
            .options(selectinload(RuleEvaluation.rule_definition))
            .where(RuleEvaluation.inspection_id == inspection_id)
        )
        if target_eval_run_id:
            stmt_eval = stmt_eval.where(RuleEvaluation.evaluation_run_id == target_eval_run_id)
        stmt_eval = stmt_eval.order_by(RuleEvaluation.evaluated_at.desc())
        eval_res = await db.execute(stmt_eval)
        evaluations = list(eval_res.scalars().all())

        # Load audit logs
        stmt_audit = (
            select(AuditLog)
            .where(AuditLog.inspection_id == inspection_id)
            .order_by(AuditLog.performed_at.desc())
        )
        audit_res = await db.execute(stmt_audit)
        audit_logs = list(audit_res.scalars().all())

        return inspection, surfaces, ocr_runs, observations, geometries, evaluations, audit_logs

    def build_evidence_graph(
        self,
        surfaces: List[InspectionSurface],
        ocr_runs: List[OCRRun],
        observations: List[Observation],
        geometries: List[PDPGeometry],
        evaluations: List[RuleEvaluation],
        adjudications: Optional[List[OCRAdjudication]] = None,
    ) -> EvidenceTraceGraph:
        """
        Assemble the backward evidence graph connecting:
        RuleEvaluation -> Observation / Geometry -> OCRAdjudication -> OCRRegion -> OCRRun -> InspectionSurface (Original Image SHA-256).
        Explicitly tracks provenance: machine-generated vs human-corrected vs manually created.
        """
        graph = EvidenceTraceGraph()
        adjudications_list = adjudications or []
        adj_by_region: Dict[uuid.UUID, OCRAdjudication] = {}
        for a in adjudications_list:
            if a.is_active:
                if a.ocr_region_id:
                    adj_by_region[a.ocr_region_id] = a

        # 1. Surface Nodes (Authentic Original Evidence)
        for s in surfaces:
            graph.add_node(
                EvidenceTraceNode(
                    node_id=str(s.id),
                    category=EvidenceCategory.ORIGINAL_IMAGE,
                    label=f"Surface: {s.surface_type.value if hasattr(s.surface_type, 'value') else s.surface_type}",
                    properties={
                        "surface_type": s.surface_type.value if hasattr(s.surface_type, "value") else str(s.surface_type),
                        "sha256_hash": s.sha256_hash,
                        "storage_reference": s.image_storage_path,
                        "dimensions": f"{s.image_width}x{s.image_height}" if s.image_width else None,
                        "provenance_type": "authentic-original-evidence",
                    },
                    parent_ids=[],
                )
            )

        # 2. OCR Run Nodes (Machine Generated)
        for r in ocr_runs:
            r_id = str(r.id)
            s_id = str(r.surface_id)
            graph.add_node(
                EvidenceTraceNode(
                    node_id=r_id,
                    category=EvidenceCategory.OCR_RUN,
                    label=f"OCR: {r.provider_name} ({r.preprocessing_variant})",
                    properties={
                        "provider": r.provider_name,
                        "status": r.status,
                        "total_regions": r.total_regions_detected,
                        "provenance_type": "machine-generated",
                    },
                    parent_ids=[s_id],
                )
            )
            graph.add_edge(r_id, s_id, "EXTRACTED_FROM_IMAGE")

            # OCR Regions (Machine Generated)
            if hasattr(r, "regions") and r.regions:
                for reg in r.regions:
                    reg_id = str(reg.id)
                    graph.add_node(
                        EvidenceTraceNode(
                            node_id=reg_id,
                            category=EvidenceCategory.OCR_REGION,
                            label=f"Token: '{reg.raw_text[:30]}'",
                            properties={
                                "raw_text": reg.raw_text,
                                "confidence": float(reg.confidence),
                                "bounding_box": reg.bounding_box,
                                "provenance_type": "machine-generated",
                            },
                            parent_ids=[r_id],
                        )
                    )
                    graph.add_edge(reg_id, r_id, "TOKEN_OF_OCR_RUN")

        # 3. Human Adjudication Nodes
        for adj in adjudications_list:
            if not adj.is_active:
                continue
            adj_id = str(adj.id)
            is_manual = (adj.correction_type == CorrectionType.REGION_CREATED)
            prov_type = "manually created" if is_manual else "human-corrected"
            parent_ids = [str(adj.ocr_region_id)] if adj.ocr_region_id else [str(adj.surface_id)]

            corr_val = adj.correction_type.value if hasattr(adj.correction_type, "value") else str(adj.correction_type)
            graph.add_node(
                EvidenceTraceNode(
                    node_id=adj_id,
                    category=EvidenceCategory.ADJUDICATION,
                    label=f"Adjudication: {adj.status} ({corr_val})",
                    properties={
                        "correction_type": corr_val,
                        "status": adj.status,
                        "original_text": adj.original_text,
                        "corrected_text": adj.corrected_text,
                        "bounding_box": adj.corrected_bounding_box,
                        "reason": adj.reason,
                        "revision": adj.revision,
                        "provenance_type": prov_type,
                    },
                    parent_ids=parent_ids,
                )
            )
            if adj.ocr_region_id:
                graph.add_edge(adj_id, str(adj.ocr_region_id), "ADJUDICATED_FROM_REGION")
            else:
                graph.add_edge(adj_id, str(adj.surface_id), "MANUAL_REGION_ON_SURFACE")

        # 4. Geometry Nodes
        for g in geometries:
            g_id = str(g.id)
            s_id = str(g.surface_id)
            graph.add_node(
                EvidenceTraceNode(
                    node_id=g_id,
                    category=EvidenceCategory.PDP_GEOMETRY,
                    label=f"PDP Geometry ({g.status})",
                    properties={
                        "is_pdp_candidate": g.is_pdp_candidate,
                        "has_calibration": g.has_calibration,
                        "pixel_area": g.pdp_pixel_area,
                        "physical_area_sq_cm": g.estimated_physical_area_sq_cm,
                        "provenance_type": "machine-generated",
                    },
                    parent_ids=[s_id],
                )
            )
            graph.add_edge(g_id, s_id, "MEASURED_FROM_SURFACE")

        # 5. Observation Nodes
        for o in observations:
            o_id = str(o.id)
            parent_ids = []

            # Determine provenance
            obs_revision = getattr(o, "revision", None) or 1
            if getattr(o, "source", None) == ObservationSource.OFFICER_INPUT:
                prov_type = "manually created"
            elif obs_revision > 1:
                prov_type = "human-corrected"
            else:
                prov_type = "machine-generated"

            # Check if linked OCR region has an active adjudication
            linked_adj = adj_by_region.get(o.ocr_region_id) if o.ocr_region_id else None
            if linked_adj:
                parent_ids.append(str(linked_adj.id))
            elif o.ocr_region_id:
                parent_ids.append(str(o.ocr_region_id))
            elif o.surface_id:
                parent_ids.append(str(o.surface_id))

            graph.add_node(
                EvidenceTraceNode(
                    node_id=o_id,
                    category=EvidenceCategory.OBSERVATION,
                    label=f"Observation: {o.field_type.value if hasattr(o.field_type, 'value') else o.field_type}",
                    properties={
                        "field_type": o.field_type.value if hasattr(o.field_type, "value") else str(o.field_type),
                        "raw_value": o.raw_value,
                        "normalized_value": o.normalized_value,
                        "status": o.status.value if hasattr(o.status, "value") else str(o.status),
                        "confidence": float(o.confidence),
                        "revision": obs_revision,
                        "provenance_type": prov_type,
                    },
                    parent_ids=parent_ids,
                )
            )
            for p in parent_ids:
                graph.add_edge(o_id, p, "DERIVED_FROM")

        # 6. Rule Evaluation Nodes
        for ev in evaluations:
            ev_id = str(ev.id)
            ev_parents = []
            refs = ev.evidence_references or {}
            
            # Link to observations
            for obs_id in refs.get("observation_ids", []):
                if str(obs_id) in graph.nodes:
                    ev_parents.append(str(obs_id))
                    graph.add_edge(ev_id, str(obs_id), "EVALUATED_AGAINST_OBSERVATION")

            # Link to OCR regions if directly referenced
            for reg_id in refs.get("source_region_ids", []):
                if str(reg_id) in graph.nodes and str(reg_id) not in ev_parents:
                    ev_parents.append(str(reg_id))
                    graph.add_edge(ev_id, str(reg_id), "SUPPORTED_BY_OCR_REGION")

            # Link to geometry if referenced
            for g_id in refs.get("geometry_ids", []):
                if str(g_id) in graph.nodes and str(g_id) not in ev_parents:
                    ev_parents.append(str(g_id))
                    graph.add_edge(ev_id, str(g_id), "CALCULATED_FROM_GEOMETRY")

            r_code = ev.rule_code or (ev.rule_definition.rule_code if ev.rule_definition else "RULE")
            outcome_val = ev.outcome.value if hasattr(ev.outcome, "value") else str(ev.outcome)

            graph.add_node(
                EvidenceTraceNode(
                    node_id=ev_id,
                    category=EvidenceCategory.RULE_EVALUATION,
                    label=f"{r_code}: {outcome_val}",
                    properties={
                        "rule_code": r_code,
                        "outcome": outcome_val,
                        "statutory_citation": ev.statutory_citation,
                        "legal_rationale": ev.legal_rationale,
                        "provenance_type": "authoritative-rule-verdict",
                    },
                    parent_ids=ev_parents,
                )
            )

        return graph

    def validate_evidence_references(
        self,
        evaluations: List[RuleEvaluation],
        observations: List[Observation],
        ocr_regions: List[OCRRegion],
        surfaces: List[InspectionSurface],
    ) -> Dict[str, Any]:
        """Verify that all referenced IDs in rule evaluations exist in the database."""
        known_obs_ids = {str(o.id) for o in observations}
        known_reg_ids = {str(r.id) for r in ocr_regions}
        known_surf_ids = {str(s.id) for s in surfaces}

        total_checked = 0
        missing = []

        for ev in evaluations:
            refs = ev.evidence_references or {}
            for obs_id in refs.get("observation_ids", []):
                total_checked += 1
                if str(obs_id) not in known_obs_ids:
                    missing.append({"type": "OBSERVATION", "id": str(obs_id), "rule_eval_id": str(ev.id)})
            for reg_id in refs.get("source_region_ids", []):
                total_checked += 1
                if str(reg_id) not in known_reg_ids:
                    missing.append({"type": "OCR_REGION", "id": str(reg_id), "rule_eval_id": str(ev.id)})

        return {
            "is_valid": len(missing) == 0,
            "total_references_checked": total_checked,
            "missing_references": missing,
        }

    async def create_evidence_snapshot(
        self,
        db: AsyncSession,
        inspection_id: uuid.UUID,
        evaluation_run_id: Optional[uuid.UUID] = None,
        created_by_id: Optional[uuid.UUID] = None,
        application_version: str = "1.0.0",
    ) -> EvidenceSnapshot:
        """
        Create an immutable EvidenceSnapshot record.
        Captures the exact perception, observations, geometries, and rule evaluations state.
        Produces a canonical JSON manifest sealed with cryptographic SHA-256.
        """
        target_eval_run_id = evaluation_run_id
        if not target_eval_run_id:
            latest_run_stmt = (
                select(RuleEvaluation.evaluation_run_id)
                .where(RuleEvaluation.inspection_id == inspection_id)
                .order_by(RuleEvaluation.evaluated_at.desc())
                .limit(1)
            )
            latest_run_res = await db.execute(latest_run_stmt)
            target_eval_run_id = latest_run_res.scalar_one_or_none()

        inspection, surfaces, ocr_runs, observations, geometries, evaluations, audit_logs = (
            await self.load_inspection_dataset(db, inspection_id, target_eval_run_id)
        )

        manifest = EvidenceBundleBuilder.build_manifest(
            inspection=inspection,
            surfaces=surfaces,
            ocr_runs=ocr_runs,
            observations=observations,
            geometries=geometries,
            evaluations=evaluations,
            audit_logs=audit_logs,
            evaluation_run_id=target_eval_run_id,
            application_version=application_version,
        )

        manifest_dict = manifest.model_dump()
        integrity_hash = calculate_canonical_json_sha256(manifest_dict)

        rule_versions = {}
        for ev in evaluations:
            rc = ev.rule_code or (ev.rule_definition.rule_code if ev.rule_definition else "RULE")
            rv = ev.rule_version or (ev.rule_definition.version if ev.rule_definition else "1.0")
            rule_versions[rc] = rv

        source_record_ids = {
            "surface_ids": [str(s.id) for s in surfaces],
            "ocr_run_ids": [str(r.id) for r in ocr_runs],
            "observation_ids": [str(o.id) for o in observations],
            "geometry_ids": [str(g.id) for g in geometries],
            "rule_evaluation_ids": [str(e.id) for e in evaluations],
            "audit_log_ids": [str(a.id) for a in audit_logs],
        }

        snapshot = EvidenceSnapshot(
            inspection_id=inspection_id,
            evaluation_run_id=target_eval_run_id,
            created_by_id=created_by_id,
            application_version=application_version,
            parser_version="ENTITY-PARSER-v1",
            normalizer_version="NORMALIZER-v1",
            ocr_provider_version="Modular OCR Engine",
            rule_versions=rule_versions,
            source_record_ids=source_record_ids,
            manifest_json=manifest_dict,
            integrity_hash=integrity_hash,
            metadata_json={
                "surfaces_count": len(surfaces),
                "ocr_runs_count": len(ocr_runs),
                "observations_count": len(observations),
                "evaluations_count": len(evaluations),
                "generated_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        db.add(snapshot)
        await db.commit()
        await db.refresh(snapshot)
        return snapshot
