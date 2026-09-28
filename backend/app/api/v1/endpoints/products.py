import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.product import Product
from app.models.label_version import LabelVersion
from app.models.inspection import Inspection
from app.models.user import User
from app.models.report import InspectionReport
from app.models.rule_evaluation import RuleEvaluation
from app.schemas.product import (
    ProductCreate,
    ProductRead,
    ProductUpdate,
    ProductLedgerItemRead,
    ProductDetailRead,
    LabelVersionBase,
    LabelVersionCreate,
    LabelVersionRead,
    LabelVersionDetailRead,
    LabelDiffResponse,
    TimelineEventRead,
    ProductInspectionItemRead,
)
from app.schemas.common import ResponseEnvelope, PaginatedResponse, PaginationMeta
from app.api.deps import get_current_user
from app.services.product.ledger_service import (
    compute_label_fingerprint,
    compare_label_versions,
    build_product_timeline,
)

router = APIRouter()

@router.get("", response_model=PaginatedResponse[ProductLedgerItemRead])
async def list_products(
    q: Optional[str] = Query(None, description="Search by brand name, product name, or SKU"),
    category: Optional[str] = Query(None, description="Filter by product category"),
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer claimed"),
    gtin: Optional[str] = Query(None, description="Filter by exact GTIN/barcode"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("brand_name", description="Field to sort by: brand_name, product_name, created_at"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List packaged commodities in the national product ledger with inspection counts
    and latest packaging label versions.
    """
    base_query = select(Product)

    if gtin:
        base_query = base_query.where(Product.gtin_barcode == gtin)
    if q:
        search_filter = or_(
            Product.brand_name.ilike(f"%{q}%"),
            Product.product_name.ilike(f"%{q}%"),
            Product.gtin_barcode.ilike(f"%{q}%"),
            Product.manufacturer_claimed.ilike(f"%{q}%"),
        )
        base_query = base_query.where(search_filter)
    if category:
        base_query = base_query.where(Product.category.ilike(f"%{category}%"))
    if manufacturer:
        base_query = base_query.where(Product.manufacturer_claimed.ilike(f"%{manufacturer}%"))

    # Total count
    count_q = select(func.count()).select_from(base_query.subquery())
    total_count = (await db.execute(count_q)).scalar_one() or 0

    # Sorting
    sort_col = getattr(Product, sort_by, Product.brand_name)
    if sort_order == "desc":
        query = base_query.order_by(desc(sort_col))
    else:
        query = base_query.order_by(asc(sort_col))

    # Pagination & Load relationships for aggregations
    offset = (page - 1) * page_size
    query = (
        query.options(
            selectinload(Product.inspections),
            selectinload(Product.label_versions),
        )
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    products = result.scalars().all()

    items: List[ProductLedgerItemRead] = []
    for p in products:
        insps = p.inspections or []
        lvs = p.label_versions or []
        
        # Sort inspections by date
        sorted_insps = sorted(insps, key=lambda x: x.initiated_at, reverse=True)
        latest_insp = sorted_insps[0] if sorted_insps else None
        
        # Latest label version
        sorted_lvs = sorted(lvs, key=lambda x: x.created_at, reverse=True)
        latest_lv = sorted_lvs[0].version_tag if sorted_lvs else None

        items.append(
            ProductLedgerItemRead(
                id=p.id,
                gtin_barcode=p.gtin_barcode,
                brand_name=p.brand_name,
                product_name=p.product_name,
                category=p.category,
                commodity_type=p.commodity_type,
                manufacturer_claimed=p.manufacturer_claimed,
                inspection_count=len(insps),
                latest_inspection_date=latest_insp.initiated_at if latest_insp else None,
                latest_label_version=latest_lv,
                latest_status=latest_insp.overall_status.value if (latest_insp and hasattr(latest_insp.overall_status, "value")) else (str(latest_insp.overall_status) if latest_insp else None),
                created_at=p.created_at,
            )
        )

    return PaginatedResponse(
        success=True,
        data=items,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_count,
            total_pages=(total_count + page_size - 1) // page_size if total_count > 0 else 1,
            has_next=page * page_size < total_count,
            has_previous=page > 1,
        ),
    )

@router.post("", response_model=ResponseEnvelope[ProductRead], status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a new packaged commodity SKU."""
    if product_in.gtin_barcode:
        existing = await db.execute(select(Product).where(Product.gtin_barcode == product_in.gtin_barcode))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with GTIN {product_in.gtin_barcode} already exists",
            )
    
    product = Product(**product_in.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ResponseEnvelope(
        success=True,
        message="Product registered successfully",
        data=ProductRead.model_validate(product),
    )

@router.get("/{product_id}", response_model=ResponseEnvelope[ProductDetailRead])
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve comprehensive product profile, historical summary stats, and known statutory declarations."""
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.inspections),
            selectinload(Product.label_versions),
        )
        .where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    insps = sorted(product.inspections or [], key=lambda x: x.initiated_at)
    first_insp = insps[0] if insps else None
    latest_insp = insps[-1] if insps else None

    lvs = sorted(product.label_versions or [], key=lambda x: x.created_at)
    latest_lv = lvs[-1] if lvs else None

    # Merge known statutory declarations from latest label version or metadata
    known_decls = {}
    if latest_lv and latest_lv.canonical_declarations:
        known_decls.update(latest_lv.canonical_declarations)
    if product.metadata_json:
        known_decls.setdefault("metadata", product.metadata_json)

    return ResponseEnvelope(
        success=True,
        data=ProductDetailRead(
            id=product.id,
            gtin_barcode=product.gtin_barcode,
            brand_name=product.brand_name,
            product_name=product.product_name,
            category=product.category,
            commodity_type=product.commodity_type,
            manufacturer_claimed=product.manufacturer_claimed,
            metadata_json=product.metadata_json,
            known_declarations=known_decls,
            inspection_count=len(insps),
            first_inspection_date=first_insp.initiated_at if first_insp else None,
            latest_inspection_date=latest_insp.initiated_at if latest_insp else None,
            latest_status=latest_insp.overall_status.value if (latest_insp and hasattr(latest_insp.overall_status, "value")) else (str(latest_insp.overall_status) if latest_insp else None),
            latest_label_version=latest_lv.version_tag if latest_lv else None,
            created_at=product.created_at,
            updated_at=product.updated_at,
        ),
    )

@router.get("/{product_id}/inspections", response_model=PaginatedResponse[ProductInspectionItemRead])
async def get_product_inspections(
    product_id: uuid.UUID,
    status_filter: Optional[str] = Query(None, description="Filter by inspection status"),
    from_date: Optional[datetime] = Query(None, description="Filter by start date"),
    to_date: Optional[datetime] = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve chronological inspections for a specific packaged commodity."""
    query = (
        select(Inspection)
        .options(
            selectinload(Inspection.inspector),
            selectinload(Inspection.label_version),
            selectinload(Inspection.evaluations),
            selectinload(Inspection.reports),
        )
        .where(Inspection.product_id == product_id)
    )

    if status_filter:
        query = query.where(Inspection.overall_status == status_filter)
    if from_date:
        query = query.where(Inspection.initiated_at >= from_date)
    if to_date:
        query = query.where(Inspection.initiated_at <= to_date)

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total_count = (await db.execute(count_q)).scalar_one() or 0

    # Paginate (newest first)
    offset = (page - 1) * page_size
    query = query.order_by(desc(Inspection.initiated_at)).offset(offset).limit(page_size)

    rows = (await db.execute(query)).scalars().all()

    items: List[ProductInspectionItemRead] = []
    for insp in rows:
        inspector_name = insp.inspector.full_name if insp.inspector else None
        inspector_badge = insp.inspector.badge_number if insp.inspector else None
        label_v = insp.label_version.version_tag if insp.label_version else None

        # Latest rule evaluation verdict
        latest_eval = insp.evaluations[-1] if insp.evaluations else None
        eval_verdict = latest_eval.outcome.value if (latest_eval and hasattr(latest_eval.outcome, "value")) else (str(latest_eval.outcome) if latest_eval else None)

        # Latest report
        latest_rep = insp.reports[-1] if insp.reports else None

        items.append(
            ProductInspectionItemRead(
                id=insp.id,
                inspection_number=insp.inspection_number,
                initiated_at=insp.initiated_at,
                completed_at=insp.completed_at,
                retail_outlet_name=insp.retail_outlet_name,
                retail_outlet_address=insp.retail_outlet_address,
                inspector_name=inspector_name,
                inspector_badge=inspector_badge,
                overall_status=insp.overall_status.value if hasattr(insp.overall_status, "value") else str(insp.overall_status),
                label_version_tag=label_v,
                rule_verdict=eval_verdict,
                has_report=latest_rep is not None,
                report_id=latest_rep.id if latest_rep else None,
                report_pdf_path=latest_rep.storage_path if latest_rep else None,
            )
        )

    return PaginatedResponse(
        success=True,
        data=items,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_count,
            total_pages=(total_count + page_size - 1) // page_size if total_count > 0 else 1,
            has_next=page * page_size < total_count,
            has_previous=page > 1,
        ),
    )

@router.get("/{product_id}/label-versions", response_model=ResponseEnvelope[List[LabelVersionDetailRead]])
async def get_product_label_versions(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all known label versions for this commodity with canonical declaration payloads."""
    query = (
        select(LabelVersion)
        .options(
            selectinload(LabelVersion.source_inspection),
            selectinload(LabelVersion.evidence_snapshot),
        )
        .where(LabelVersion.product_id == product_id)
        .order_by(asc(LabelVersion.created_at))
    )
    rows = (await db.execute(query)).scalars().all()

    items: List[LabelVersionDetailRead] = []
    for lv in rows:
        source_num = lv.source_inspection.inspection_number if lv.source_inspection else None
        items.append(
            LabelVersionDetailRead(
                id=lv.id,
                product_id=lv.product_id,
                version_tag=lv.version_tag,
                version_fingerprint=lv.version_fingerprint,
                canonical_declarations=lv.canonical_declarations or {},
                source_inspection_id=lv.source_inspection_id,
                source_inspection_number=source_num,
                evidence_snapshot_id=lv.evidence_snapshot_id,
                notes=lv.notes,
                effective_from=lv.effective_from,
                effective_to=lv.effective_to,
                created_at=lv.created_at,
            )
        )

    return ResponseEnvelope(success=True, data=items)

@router.post(
    "/{product_id}/label-versions",
    response_model=ResponseEnvelope[LabelVersionRead],
    status_code=status.HTTP_201_CREATED,
)
async def create_product_label_version(
    product_id: uuid.UUID,
    payload: LabelVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a new packaging label revision for a product."""
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    fingerprint = payload.version_fingerprint or compute_label_fingerprint(payload.canonical_declarations)

    lv = LabelVersion(
        product_id=product_id,
        version_tag=payload.version_tag,
        canonical_declarations=payload.canonical_declarations,
        visual_layout_hash=payload.visual_layout_hash,
        version_fingerprint=fingerprint,
        source_inspection_id=payload.source_inspection_id,
        evidence_snapshot_id=payload.evidence_snapshot_id,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        notes=payload.notes,
        metadata_json=payload.metadata_json,
    )
    db.add(lv)
    await db.commit()
    await db.refresh(lv)
    return ResponseEnvelope(
        success=True,
        message="Label version registered successfully",
        data=LabelVersionRead.model_validate(lv),
    )

@router.get("/{product_id}/changes", response_model=ResponseEnvelope[LabelDiffResponse])
async def get_label_version_changes(
    product_id: uuid.UUID,
    from_version_id: uuid.UUID = Query(..., description="Base label version ID"),
    to_version_id: uuid.UUID = Query(..., description="Target label version ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Perform deterministic historical comparison between two label versions of a commodity.
    Categorizes statutory declarations into Changed, Added, Removed, and Unchanged fields.
    """
    from_v = (await db.execute(select(LabelVersion).where(LabelVersion.id == from_version_id, LabelVersion.product_id == product_id))).scalar_one_or_none()
    if not from_v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="From label version not found")

    to_v = (await db.execute(select(LabelVersion).where(LabelVersion.id == to_version_id, LabelVersion.product_id == product_id))).scalar_one_or_none()
    if not to_v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="To label version not found")

    diff = compare_label_versions(from_v, to_v)
    return ResponseEnvelope(success=True, data=diff)

@router.get("/{product_id}/timeline", response_model=ResponseEnvelope[List[TimelineEventRead]])
async def get_product_timeline_events(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve comprehensive chronological product lifecycle timeline.
    Includes registrations, inspections, surface captures, OCR, adjudications, rule evaluations, label versions, and reports.
    """
    events = await build_product_timeline(db, product_id)
    return ResponseEnvelope(success=True, data=events)
