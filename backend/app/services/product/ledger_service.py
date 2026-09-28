import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc
from sqlalchemy.orm import selectinload

from app.models.product import Product
from app.models.label_version import LabelVersion
from app.models.inspection import Inspection
from app.models.surface import InspectionSurface
from app.models.ocr_run import OCRRun
from app.models.entity_run import EntityParsingRun
from app.models.observation import Observation
from app.models.adjudication import OCRAdjudication
from app.models.rule_evaluation import RuleEvaluation
from app.models.report import InspectionReport
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.product import (
    FieldComparisonItem,
    LabelDiffResponse,
    TimelineEventRead,
)

STATUTORY_FIELD_LABELS: Dict[str, str] = {
    "MRP": "Maximum Retail Price (MRP)",
    "NET_QUANTITY": "Net Quantity",
    "MANUFACTURER_NAME": "Manufacturer Name & Address",
    "PACKER_NAME": "Packer Name & Address",
    "IMPORTER_NAME": "Importer Name & Address",
    "COUNTRY_OF_ORIGIN": "Country of Origin",
    "CONSUMER_CARE_EMAIL": "Consumer Care Email",
    "CONSUMER_CARE_PHONE": "Consumer Care Phone",
    "CONSUMER_CARE_ADDRESS": "Consumer Care Address",
    "DATE_OF_MANUFACTURE": "Date of Manufacture",
    "DATE_OF_PACKING": "Date of Packaging",
    "BEST_BEFORE_DATE": "Best Before Date",
    "EXPIRY_DATE": "Expiry Date",
    "BATCH_NUMBER": "Batch / Lot Code",
    "UNIT_SALE_PRICE": "Unit Sale Price (USP)",
    "GENERIC_NAME": "Common / Generic Name of Commodity",
}

def canonicalize_declaration_value(val: Any) -> str:
    """Helper to convert any normalized or raw declaration into a stable canonical string."""
    if val is None:
        return ""
    if isinstance(val, dict):
        # Format dictionary deterministically (sorted keys)
        if "formatted" in val:
            return str(val["formatted"]).strip().lower()
        if "value" in val:
            unit = val.get("unit", "")
            return f"{val['value']} {unit}".strip().lower()
        return json.dumps(val, sort_keys=True)
    return str(val).strip().lower()

def compute_label_fingerprint(canonical_declarations: Dict[str, Any]) -> str:
    """
    Deterministic SHA-256 fingerprint generated from canonical, sorted statutory declarations.
    Does NOT rely on AI or probabilistic scoring.
    """
    canonical_dict = {}
    for k in sorted(canonical_declarations.keys()):
        raw_val = canonical_declarations[k]
        canonical_dict[str(k).upper()] = canonicalize_declaration_value(raw_val)
    
    canonical_json = json.dumps(canonical_dict, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

def compare_label_versions(
    from_version: LabelVersion,
    to_version: LabelVersion,
) -> LabelDiffResponse:
    """
    Deterministic historical comparison between two product label versions.
    Categorizes fields into Changed, Added, Removed, and Unchanged declarations.
    """
    prev_decls = from_version.canonical_declarations or {}
    curr_decls = to_version.canonical_declarations or {}

    all_keys = sorted(list(set(prev_decls.keys()) | set(curr_decls.keys())))

    changed_fields: List[FieldComparisonItem] = []
    added_fields: List[FieldComparisonItem] = []
    removed_fields: List[FieldComparisonItem] = []
    unchanged_fields: List[FieldComparisonItem] = []

    for key in all_keys:
        label = STATUTORY_FIELD_LABELS.get(key, key.replace("_", " ").title())
        has_prev = key in prev_decls
        has_curr = key in curr_decls

        if has_prev and not has_curr:
            removed_fields.append(
                FieldComparisonItem(
                    field=key,
                    field_label=label,
                    prev_value=prev_decls[key],
                    curr_value=None,
                    prev_source="Previous Label Version",
                    curr_source=None,
                )
            )
        elif not has_prev and has_curr:
            added_fields.append(
                FieldComparisonItem(
                    field=key,
                    field_label=label,
                    prev_value=None,
                    curr_value=curr_decls[key],
                    prev_source=None,
                    curr_source="Current Label Version",
                )
            )
        else:
            prev_canon = canonicalize_declaration_value(prev_decls[key])
            curr_canon = canonicalize_declaration_value(curr_decls[key])

            if prev_canon != curr_canon:
                changed_fields.append(
                    FieldComparisonItem(
                        field=key,
                        field_label=label,
                        prev_value=prev_decls[key],
                        curr_value=curr_decls[key],
                        prev_source=f"Version {from_version.version_tag}",
                        curr_source=f"Version {to_version.version_tag}",
                    )
                )
            else:
                unchanged_fields.append(
                    FieldComparisonItem(
                        field=key,
                        field_label=label,
                        prev_value=prev_decls[key],
                        curr_value=curr_decls[key],
                        prev_source=f"Version {from_version.version_tag}",
                        curr_source=f"Version {to_version.version_tag}",
                    )
                )

    total_changes = len(changed_fields) + len(added_fields) + len(removed_fields)

    return LabelDiffResponse(
        from_version_id=from_version.id,
        from_version_tag=from_version.version_tag,
        to_version_id=to_version.id,
        to_version_tag=to_version.version_tag,
        changed_fields=changed_fields,
        added_fields=added_fields,
        removed_fields=removed_fields,
        unchanged_fields=unchanged_fields,
        total_changes=total_changes,
    )

async def resolve_or_create_label_version(
    db: AsyncSession,
    product_id: uuid.UUID,
    inspection_id: uuid.UUID,
    canonical_declarations: Dict[str, Any],
    evidence_snapshot_id: Optional[uuid.UUID] = None,
    notes: Optional[str] = None,
) -> LabelVersion:
    """
    Resolves an existing label version by deterministic fingerprint,
    or creates a new numbered label version (v1.0, v2.0...) preserving historical identity.
    """
    fingerprint = compute_label_fingerprint(canonical_declarations)

    # Check if this exact fingerprint already exists for this product
    existing_q = select(LabelVersion).where(
        LabelVersion.product_id == product_id,
        LabelVersion.version_fingerprint == fingerprint,
    )
    res = await db.execute(existing_q)
    existing = res.scalar_one_or_none()
    if existing:
        return existing

    # Count existing versions for this product to determine version tag
    count_q = select(func.count()).select_from(LabelVersion).where(LabelVersion.product_id == product_id)
    count_res = await db.execute(count_q)
    version_count = count_res.scalar_one() or 0
    version_tag = f"v{version_count + 1}.0"

    new_version = LabelVersion(
        product_id=product_id,
        version_tag=version_tag,
        version_fingerprint=fingerprint,
        canonical_declarations=canonical_declarations,
        source_inspection_id=inspection_id,
        evidence_snapshot_id=evidence_snapshot_id,
        notes=notes or f"Generated from Inspection {inspection_id} declarations",
    )
    db.add(new_version)
    await db.commit()
    await db.refresh(new_version)
    return new_version

async def build_product_timeline(
    db: AsyncSession,
    product_id: uuid.UUID,
) -> List[TimelineEventRead]:
    """
    Constructs a comprehensive, chronologically sorted event stream for a product
    aggregating across inspections, surface captures, OCR, human adjudications, rule evaluations,
    label versions, and official PDF report generation.
    """
    events: List[TimelineEventRead] = []

    # 1. Product Registration Event
    prod_q = select(Product).where(Product.id == product_id)
    prod_res = await db.execute(prod_q)
    product = prod_res.scalar_one_or_none()
    if not product:
        return []

    events.append(
        TimelineEventRead(
            event_id=f"prod-reg-{product.id}",
            event_type="PRODUCT_REGISTERED",
            timestamp=product.created_at,
            title=f"Commodity Registered: {product.brand_name} {product.product_name}",
            description=f"Packaged commodity registered with category '{product.category or 'General'}' and GTIN {product.gtin_barcode or 'N/A'}.",
            metadata={"product_id": str(product.id), "brand": product.brand_name},
        )
    )

    # 2. Fetch all inspections associated with this product
    insps_q = (
        select(Inspection)
        .options(
            selectinload(Inspection.inspector),
            selectinload(Inspection.label_version),
            selectinload(Inspection.surfaces),
            selectinload(Inspection.evaluations),
            selectinload(Inspection.reports),
        )
        .where(Inspection.product_id == product_id)
        .order_by(Inspection.initiated_at.asc())
    )
    insps_res = await db.execute(insps_q)
    inspections = insps_res.scalars().all()
    inspection_ids = [i.id for i in inspections]

    for insp in inspections:
        insp_id_str = str(insp.id)
        inspector_name = insp.inspector.full_name if insp.inspector else "Authorized Inspector"
        inspector_badge = insp.inspector.badge_number if insp.inspector else None

        # Inspection Creation
        events.append(
            TimelineEventRead(
                event_id=f"insp-init-{insp.id}",
                event_type="INSPECTION_CREATED",
                timestamp=insp.initiated_at,
                title=f"Inspection Initiated ({insp.inspection_number})",
                description=f"Physical inspection initiated at '{insp.retail_outlet_name or 'Field Site'}' by {inspector_name}.",
                actor_name=inspector_name,
                actor_role="INSPECTOR",
                badge_number=inspector_badge,
                inspection_id=insp.id,
                inspection_number=insp.inspection_number,
                metadata={"status": insp.overall_status.value if hasattr(insp.overall_status, "value") else str(insp.overall_status)},
            )
        )

        # Surfaces captured
        for surf in insp.surfaces:
            surf_type_label = surf.surface_type.value if hasattr(surf.surface_type, "value") else str(surf.surface_type)
            events.append(
                TimelineEventRead(
                    event_id=f"surf-cap-{surf.id}",
                    event_type="EVIDENCE_CAPTURED",
                    timestamp=surf.captured_at or surf.created_at,
                    title=f"Evidence Surface Captured ({surf_type_label})",
                    description=f"Package surface '{surf_type_label}' ingested with SHA-256 {surf.sha256_hash[:16]}...",
                    inspection_id=insp.id,
                    inspection_number=insp.inspection_number,
                    metadata={"surface_id": str(surf.id), "sha256": surf.sha256_hash},
                )
            )

        # Rule Evaluations
        for ev in insp.evaluations:
            verdict_str = ev.outcome.value if hasattr(ev.outcome, "value") else str(ev.outcome)
            events.append(
                TimelineEventRead(
                    event_id=f"rule-eval-{ev.id}",
                    event_type="RULES_EVALUATED",
                    timestamp=ev.created_at,
                    title=f"Deterministic Rule Evaluation: {verdict_str}",
                    description=f"Rule engine evaluated packaged commodity rules. Verdict: {verdict_str}.",
                    inspection_id=insp.id,
                    inspection_number=insp.inspection_number,
                    metadata={"verdict": verdict_str, "evaluation_run_id": str(ev.id)},
                )
            )

        # Reports Generated
        for rep in insp.reports:
            events.append(
                TimelineEventRead(
                    event_id=f"report-gen-{rep.id}",
                    event_type="REPORT_GENERATED",
                    timestamp=rep.created_at,
                    title=f"Legal Dossier PDF Generated (v{rep.report_version})",
                    description=f"Statutory inspection dossier produced: {rep.storage_path} (SHA-256: {rep.sha256_hash[:16]}...).",
                    actor_name=inspector_name,
                    inspection_id=insp.id,
                    inspection_number=insp.inspection_number,
                    metadata={"report_id": str(rep.id), "storage_path": rep.storage_path, "sha256": rep.sha256_hash},
                )
            )

    # 3. Label Versions Observed
    lvs_q = (
        select(LabelVersion)
        .options(selectinload(LabelVersion.source_inspection))
        .where(LabelVersion.product_id == product_id)
        .order_by(LabelVersion.created_at.asc())
    )
    lvs_res = await db.execute(lvs_q)
    label_versions = lvs_res.scalars().all()

    for lv in label_versions:
        source_num = lv.source_inspection.inspection_number if lv.source_inspection else "Baseline"
        events.append(
            TimelineEventRead(
                event_id=f"lv-obs-{lv.id}",
                event_type="LABEL_VERSION_OBSERVED",
                timestamp=lv.created_at,
                title=f"Label Version Observed ({lv.version_tag})",
                description=f"Statutory packaging declaration state identified with fingerprint {lv.version_fingerprint[:16] if lv.version_fingerprint else 'N/A'}... Source: {source_num}.",
                metadata={"version_tag": lv.version_tag, "fingerprint": lv.version_fingerprint, "declarations_count": len(lv.canonical_declarations or {})},
            )
        )

    # 4. Human Adjudications & Audit Logs
    if inspection_ids:
        adj_q = (
            select(OCRAdjudication)
            .options(selectinload(OCRAdjudication.created_by))
            .where(OCRAdjudication.inspection_id.in_(inspection_ids))
            .order_by(OCRAdjudication.created_at.asc())
        )
        adj_res = await db.execute(adj_q)
        adjudications = adj_res.scalars().all()

        for adj in adjudications:
            officer = adj.created_by.full_name if adj.created_by else "Authorized Adjudicator"
            badge = adj.created_by.badge_number if adj.created_by else None
            corr_type = adj.correction_type.value if hasattr(adj.correction_type, "value") else str(adj.correction_type)
            events.append(
                TimelineEventRead(
                    event_id=f"adj-act-{adj.id}",
                    event_type="HUMAN_ADJUDICATION",
                    timestamp=adj.created_at,
                    title=f"Human Adjudication: {corr_type.replace('_', ' ').title()}",
                    description=f"Adjudicator {officer} corrected packaging evidence: '{adj.reason or 'Statutory observation verified'}'.",
                    actor_name=officer,
                    actor_role="ADJUDICATOR",
                    badge_number=badge,
                    inspection_id=adj.inspection_id,
                    metadata={"correction_type": corr_type, "status": adj.status},
                )
            )

    # Sort all events chronologically (oldest to newest)
    events.sort(key=lambda x: x.timestamp)
    return events
