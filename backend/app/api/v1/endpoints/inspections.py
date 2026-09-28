import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.inspection import Inspection
from app.models.product import Product
from app.models.surface import InspectionSurface
from app.models.user import User
from app.models.report import InspectionReport
from app.models.evidence import EvidenceSnapshot
from app.models.audit_log import AuditLog
from app.models.adjudication import OCRAdjudication
from app.models.enums import InspectionOverallStatus, SurfaceType, UserRole
from app.schemas.inspection import (
    InspectionCreate,
    InspectionRead,
    InspectionDetailRead,
    InspectionUpdate,
)
from app.schemas.surface import ImageUploadResponse
from app.schemas.common import ResponseEnvelope
from app.schemas.ocr import (
    OCRRunRequest,
    OCRRunResponse,
    OCRRunListResponse,
    OCRRegionResponse,
)
from app.schemas.entity import (
    EntityParseRequest,
    EntityRunResponse,
    EntityRunListResponse,
)
from app.schemas.geometry import (
    PDPGeometryRequest,
    PDPGeometryResponse,
    PDPGeometryListResponse,
)
from app.schemas.rule import (
    RuleEvaluationRequest,
    InspectionComplianceSummaryResponse,
    RuleEvaluationRead,
)
from app.schemas.report import (
    ReportGenerateRequest,
    ReportRead,
    EvidenceSnapshotRead,
    EvidenceBundleResponse,
)
from app.models.ocr_run import OCRRun
from app.models.entity_run import EntityParsingRun
from app.models.pdp_geometry import PDPGeometry
from app.models.rule_evaluation import RuleEvaluation
from app.api.deps import (
    get_current_user,
    get_image_ingestion_service,
    get_storage_service,
    get_ocr_processing_service,
    get_entity_parsing_service,
    get_pdp_geometry_service,
    get_rule_engine_service,
    get_evidence_service,
    get_pdf_generator,
)
from app.services.image_ingestion import ImageIngestionService
from app.services.storage.base import BaseStorageService
from app.services.ocr.service import OCRProcessingService
from app.services.entity.parser import EntityParsingService
from app.services.geometry.pdp import PDPGeometryService
from app.services.geometry.models import CalibrationInput
from app.services.rules.engine import DeterministicRuleEngine
from app.services.evidence.service import EvidenceService
from app.services.evidence.bundle import EvidenceBundleBuilder
from app.services.evidence.integrity import calculate_canonical_json_sha256
from app.services.report.pdf_generator import DossierPDFGenerator
from app.services.report.models import DossierOptions

router = APIRouter()

@router.get("", response_model=ResponseEnvelope[List[InspectionRead]])
async def list_inspections(
    status_filter: Optional[InspectionOverallStatus] = Query(None, alias="status"),
    retailer: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List inspection sessions with filtering capabilities."""
    query = select(Inspection)
    if status_filter:
        query = query.where(Inspection.overall_status == status_filter)
    if retailer:
        query = query.where(Inspection.retail_outlet_name.ilike(f"%{retailer}%"))
    
    result = await db.execute(query.order_by(Inspection.initiated_at.desc()).limit(100))
    inspections = result.scalars().all()
    return ResponseEnvelope(
        success=True,
        data=[InspectionRead.model_validate(i) for i in inspections]
    )

@router.post("", response_model=ResponseEnvelope[InspectionRead], status_code=status.HTTP_201_CREATED)
async def create_inspection(
    inspection_in: InspectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Initialize a new point-in-time Legal Metrology inspection session.
    Product can be linked immediately or attached after package scanning.
    """
    if inspection_in.product_id:
        prod = await db.execute(select(Product).where(Product.id == inspection_in.product_id))
        if not prod.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked product not found")

    # Generate sequential or unique inspection number if not provided
    inspection_num = inspection_in.inspection_number or f"LMR-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    inspection = Inspection(
        inspection_number=inspection_num,
        product_id=inspection_in.product_id,
        inspector_id=current_user.id,
        retail_outlet_name=inspection_in.retail_outlet_name,
        retail_outlet_address=inspection_in.retail_outlet_address,
        geo_coordinates=inspection_in.geo_coordinates,
        notes=inspection_in.notes,
        overall_status=InspectionOverallStatus.PENDING,
        initiated_at=datetime.now(timezone.utc),
    )
    db.add(inspection)
    await db.commit()
    await db.refresh(inspection)
    return ResponseEnvelope(
        success=True,
        message="Inspection initialized",
        data=InspectionRead.model_validate(inspection)
    )

@router.get("/{inspection_id}", response_model=ResponseEnvelope[InspectionDetailRead])
async def get_inspection(
    inspection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve comprehensive aggregate view of an inspection:
    includes linked product, surfaces, active observations, rule evaluations, and evidence items.
    """
    query = (
        select(Inspection)
        .options(
            selectinload(Inspection.product),
            selectinload(Inspection.surfaces),
            selectinload(Inspection.observations),
            selectinload(Inspection.evaluations),
            selectinload(Inspection.evidence_items),
        )
        .where(Inspection.id == inspection_id)
    )
    result = await db.execute(query)
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    return ResponseEnvelope(
        success=True,
        data=InspectionDetailRead.model_validate(inspection)
    )

@router.patch("/{inspection_id}", response_model=ResponseEnvelope[InspectionRead])
async def update_inspection(
    inspection_id: uuid.UUID,
    update_in: InspectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update inspection status, notes, or mark as completed."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    update_data = update_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(inspection, field, value)

    await db.commit()
    await db.refresh(inspection)
    return ResponseEnvelope(
        success=True,
        message="Inspection updated",
        data=InspectionRead.model_validate(inspection)
    )

# ----------------------------------------------------------------------
# PHASE 2: SIX-SURFACE IMAGE INGESTION & STORAGE MANAGEMENT
# ----------------------------------------------------------------------

def _verify_inspection_access(inspection: Inspection, current_user: User):
    """
    RBAC enforcement:
    Only the assigned inspector or supervisory roles (Adjudicator, Admin, Auditor)
    may access or modify inspection surfaces.
    """
    if current_user.role in [UserRole.ADJUDICATOR, UserRole.ADMIN, UserRole.AUDITOR]:
        return
    if inspection.inspector_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You are not authorized to access or modify this inspection."
        )

@router.post(
    "/{inspection_id}/surfaces/{surface_type}/images",
    response_model=ResponseEnvelope[ImageUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload package surface image",
    description=(
        "Securely upload an authentic packaged commodity surface image. "
        "Validates actual image content (JPEG, PNG, WEBP), enforces size/dimension bounds, "
        "calculates cryptographic SHA-256 integrity hash, stores raw original bytes unchanged, "
        "and checks for duplicate content across inspections."
    ),
)
async def upload_surface_image(
    inspection_id: uuid.UUID,
    surface_type: SurfaceType,
    file: UploadFile = File(..., description="Raw image file (JPEG, PNG, WEBP)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ingestion_service: ImageIngestionService = Depends(get_image_ingestion_service),
):
    """Securely upload and ingest an original package surface image."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    _verify_inspection_access(inspection, current_user)

    # Read binary bytes
    content_bytes = await file.read()

    try:
        image_metadata = await ingestion_service.ingest_image(
            db=db,
            inspection=inspection,
            surface_type=surface_type,
            content_bytes=content_bytes,
            original_filename=file.filename,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return ResponseEnvelope(
        success=True,
        message="Package surface image ingested successfully",
        data=image_metadata
    )

@router.get(
    "/{inspection_id}/surfaces/{surface_type}/images",
    response_model=ResponseEnvelope[List[ImageUploadResponse]],
    summary="List images for a package surface",
    description="Retrieve all uploaded images associated with a specific package surface for an inspection.",
)
async def list_surface_images(
    inspection_id: uuid.UUID,
    surface_type: SurfaceType,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all captured images for a specific surface on an inspection."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    _verify_inspection_access(inspection, current_user)

    query = (
        select(InspectionSurface)
        .where(
            InspectionSurface.inspection_id == inspection_id,
            InspectionSurface.surface_type == surface_type,
        )
        .order_by(InspectionSurface.captured_at.asc())
    )
    s_result = await db.execute(query)
    surfaces = s_result.scalars().all()

    return ResponseEnvelope(
        success=True,
        data=[
            ImageUploadResponse(
                id=s.id,
                inspection_id=s.inspection_id,
                surface_type=s.surface_type,
                original_filename=s.original_filename,
                mime_type=s.mime_type or "image/jpeg",
                detected_format=s.detected_format or "JPEG",
                file_size_bytes=s.file_size_bytes or 0,
                image_width=s.image_width or 0,
                image_height=s.image_height or 0,
                sha256_hash=s.sha256_hash,
                storage_reference=s.image_storage_path,
                is_duplicate=s.quality_metrics.get("is_duplicate_content", False),
                duplicate_of_surface_id=uuid.UUID(s.quality_metrics["duplicate_of_surface_id"]) if s.quality_metrics.get("duplicate_of_surface_id") else None,
                captured_at=s.captured_at,
                quality_metrics=s.quality_metrics,
            )
            for s in surfaces
        ]
    )

@router.get(
    "/{inspection_id}/images/{image_id}",
    response_model=ResponseEnvelope[ImageUploadResponse],
    summary="Get image metadata",
    description="Retrieve metadata for a specific ingested package image without revealing filesystem paths.",
)
async def get_image_metadata(
    inspection_id: uuid.UUID,
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve metadata for a specific image."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    _verify_inspection_access(inspection, current_user)

    s_res = await db.execute(
        select(InspectionSurface).where(
            InspectionSurface.inspection_id == inspection_id,
            InspectionSurface.id == image_id,
        )
    )
    surface = s_res.scalar_one_or_none()
    if not surface:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found for this inspection")

    return ResponseEnvelope(
        success=True,
        data=ImageUploadResponse(
            id=surface.id,
            inspection_id=surface.inspection_id,
            surface_type=surface.surface_type,
            original_filename=surface.original_filename,
            mime_type=surface.mime_type or "image/jpeg",
            detected_format=surface.detected_format or "JPEG",
            file_size_bytes=surface.file_size_bytes or 0,
            image_width=surface.image_width or 0,
            image_height=surface.image_height or 0,
            sha256_hash=surface.sha256_hash,
            storage_reference=surface.image_storage_path,
            is_duplicate=surface.quality_metrics.get("is_duplicate_content", False),
            duplicate_of_surface_id=uuid.UUID(surface.quality_metrics["duplicate_of_surface_id"]) if surface.quality_metrics.get("duplicate_of_surface_id") else None,
            captured_at=surface.captured_at,
            quality_metrics=surface.quality_metrics,
        )
    )

@router.get(
    "/{inspection_id}/images/{image_id}/content",
    summary="Retrieve original image content",
    description="Stream/download original unchanged image bytes using application-controlled storage reference.",
)
async def get_image_content(
    inspection_id: uuid.UUID,
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage_service: BaseStorageService = Depends(get_storage_service),
):
    """Retrieve raw original image bytes through storage abstraction."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    _verify_inspection_access(inspection, current_user)

    s_res = await db.execute(
        select(InspectionSurface).where(
            InspectionSurface.inspection_id == inspection_id,
            InspectionSurface.id == image_id,
        )
    )
    surface = s_res.scalar_one_or_none()
    if not surface:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found for this inspection")

    try:
        image_bytes = await storage_service.retrieve(surface.image_storage_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image binary not found in storage repository."
        )

    safe_filename = surface.original_filename or f"{surface.id}.jpg"
    return Response(
        content=image_bytes,
        media_type=surface.mime_type or "image/jpeg",
        headers={
            "Content-Disposition": f'inline; filename="{safe_filename}"',
            "Cache-Control": "private, max-age=3600",
            "X-Content-SHA256": surface.sha256_hash,
        }
    )

# ----------------------------------------------------------------------
# PHASE 3: COMPUTER VISION PREPROCESSING & MODULAR OCR PIPELINE
# ----------------------------------------------------------------------

@router.post(
    "/{inspection_id}/images/{image_id}/ocr",
    response_model=ResponseEnvelope[OCRRunResponse],
    status_code=status.HTTP_200_OK,
    summary="Execute OCR on package surface image",
    description=(
        "Execute CV preprocessing and Optical Character Recognition on an ingested image. "
        "Preserves original image bytes unchanged, generates configurable processed derivatives, "
        "runs configured OCR provider (e.g., Tesseract OCR or Mock provider), validates normalized bounding "
        "boxes in [0, 1] space, and stores an immutable OCRRun record with fine-grained OCRRegions."
    ),
)
async def run_image_ocr(
    inspection_id: uuid.UUID,
    image_id: uuid.UUID,
    request: Optional[OCRRunRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ocr_service: OCRProcessingService = Depends(get_ocr_processing_service),
):
    """Execute OCR pipeline on a package surface image."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    _verify_inspection_access(inspection, current_user)

    s_res = await db.execute(
        select(InspectionSurface).where(
            InspectionSurface.inspection_id == inspection_id,
            InspectionSurface.id == image_id,
        )
    )
    surface = s_res.scalar_one_or_none()
    if not surface:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found for this inspection")

    variant = request.preprocessing_variant if request and request.preprocessing_variant else "original"
    provider_pref = (request.provider_name or request.provider) if request else None

    try:
        ocr_run = await ocr_service.execute_ocr_pipeline(
            db=db,
            inspection=inspection,
            surface=surface,
            preprocessing_variant=variant,
            provider_name=provider_pref,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"OCR execution failed: {str(e)}")

    # Ensure regions are loaded for response
    run_with_regions = (
        await db.execute(
            select(OCRRun)
            .options(selectinload(OCRRun.regions))
            .where(OCRRun.id == ocr_run.id)
        )
    ).scalar_one()

    ocr_response = OCRRunResponse.model_validate(run_with_regions)
    ocr_response.surface = surface.surface_type.value if hasattr(surface.surface_type, "value") else str(surface.surface_type)

    return ResponseEnvelope(
        success=True,
        message=f"OCR execution completed with status: {run_with_regions.status}",
        data=ocr_response,
    )

@router.get(
    "/{inspection_id}/images/{image_id}/ocr",
    response_model=ResponseEnvelope[OCRRunListResponse],
    summary="Retrieve historical OCR runs for image",
    description=(
        "Retrieve all historical OCR runs and recognized regions for a package surface image. "
        "Supports full traceability across varying preprocessing variants and OCR providers."
    ),
)
async def get_image_ocr_history(
    inspection_id: uuid.UUID,
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all historical OCR executions performed on this image."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    _verify_inspection_access(inspection, current_user)

    s_res = await db.execute(
        select(InspectionSurface).where(
            InspectionSurface.inspection_id == inspection_id,
            InspectionSurface.id == image_id,
        )
    )
    surface = s_res.scalar_one_or_none()
    if not surface:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found for this inspection")

    query = (
        select(OCRRun)
        .options(selectinload(OCRRun.regions))
        .where(
            OCRRun.inspection_id == inspection_id,
            OCRRun.surface_id == image_id,
        )
        .order_by(OCRRun.executed_at.desc())
    )
    res = await db.execute(query)
    runs = res.scalars().all()

    return ResponseEnvelope(
        success=True,
        data=OCRRunListResponse(
            surface_id=image_id,
            total_runs=len(runs),
            runs=[OCRRunResponse.model_validate(r) for r in runs],
        ),
    )

# ----------------------------------------------------------------------
# PHASE 4: ENTITY PARSING, NORMALIZATION & PDP GEOMETRY ANALYSIS
# ----------------------------------------------------------------------

@router.post(
    "/{inspection_id}/images/{image_id}/entities",
    response_model=ResponseEnvelope[EntityRunResponse],
    status_code=status.HTTP_200_OK,
    summary="Parse statutory entities from OCR evidence",
    description=(
        "Execute semantic entity parsing and normalization on OCR regions for a package surface image. "
        "Extracts mandatory Legal Metrology statutory fields (product name, manufacturer, packer, importer, "
        "net quantity with base conversions, MRP, dates, consumer care, country of origin, unit sale price), "
        "detects conflicts, flags ambiguities, and creates structured Observation entities."
    ),
)
async def run_entity_parsing(
    inspection_id: uuid.UUID,
    image_id: uuid.UUID,
    request: Optional[EntityParseRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    entity_service: EntityParsingService = Depends(get_entity_parsing_service),
):
    """Execute entity parsing on OCR perception evidence."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    _verify_inspection_access(inspection, current_user)

    s_res = await db.execute(
        select(InspectionSurface).where(
            InspectionSurface.inspection_id == inspection_id,
            InspectionSurface.id == image_id,
        )
    )
    surface = s_res.scalar_one_or_none()
    if not surface:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found for this inspection")

    ocr_run_id = request.ocr_run_id if request and request.ocr_run_id else None

    try:
        entity_run = await entity_service.execute_entity_pipeline(
            db=db,
            inspection=inspection,
            surface=surface,
            ocr_run_id=ocr_run_id,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Entity parsing failed: {str(e)}")

    # Ensure observations relationship is loaded
    run_with_obs = (
        await db.execute(
            select(EntityParsingRun)
            .options(selectinload(EntityParsingRun.observations))
            .where(EntityParsingRun.id == entity_run.id)
        )
    ).scalar_one()

    return ResponseEnvelope(
        success=True,
        message=f"Entity parsing execution completed with status: {run_with_obs.status}",
        data=EntityRunResponse.model_validate(run_with_obs),
    )

@router.get(
    "/{inspection_id}/images/{image_id}/entities",
    response_model=ResponseEnvelope[EntityRunListResponse],
    summary="Retrieve historical entity parsing runs",
    description="Retrieve all historical entity parsing runs and generated observations for a surface image.",
)
async def get_entity_parsing_history(
    inspection_id: uuid.UUID,
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    entity_service: EntityParsingService = Depends(get_entity_parsing_service),
):
    """Retrieve historical entity parsing runs."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    _verify_inspection_access(inspection, current_user)

    s_res = await db.execute(
        select(InspectionSurface).where(
            InspectionSurface.inspection_id == inspection_id,
            InspectionSurface.id == image_id,
        )
    )
    surface = s_res.scalar_one_or_none()
    if not surface:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found for this inspection")

    runs = await entity_service.get_entity_runs_for_surface(db, surface.id)

    return ResponseEnvelope(
        success=True,
        data=EntityRunListResponse(
            surface_id=image_id,
            total_runs=len(runs),
            runs=[EntityRunResponse.model_validate(r) for r in runs],
        ),
    )

@router.post(
    "/{inspection_id}/images/{image_id}/geometry",
    response_model=ResponseEnvelope[PDPGeometryResponse],
    status_code=status.HTTP_200_OK,
    summary="Analyze Principal Display Panel (PDP) geometry",
    description=(
        "Analyze Principal Display Panel geometry, pixel areas, text height geometry, and declaration "
        "spatial placement. Physical calibration is applied when authentic scale is provided; otherwise "
        "physical dimensions remain explicitly uncalibrated/None with zero fabrication."
    ),
)
async def analyze_pdp_geometry(
    inspection_id: uuid.UUID,
    image_id: uuid.UUID,
    request: Optional[PDPGeometryRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    geometry_service: PDPGeometryService = Depends(get_pdp_geometry_service),
):
    """Execute PDP geometry analysis on an inspection surface image."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    _verify_inspection_access(inspection, current_user)

    s_res = await db.execute(
        select(InspectionSurface).where(
            InspectionSurface.inspection_id == inspection_id,
            InspectionSurface.id == image_id,
        )
    )
    surface = s_res.scalar_one_or_none()
    if not surface:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found for this inspection")

    calib_input = None
    if request:
        calib_input = CalibrationInput(
            scale_px_per_mm=request.scale_px_per_mm,
            reference_dimension_mm=request.reference_dimension_mm,
            reference_dimension_px=request.reference_dimension_px,
            calibration_source=request.calibration_source,
        )

    try:
        geom_run = await geometry_service.analyze_pdp_geometry(
            db=db,
            inspection=inspection,
            surface=surface,
            calibration=calib_input,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Geometry analysis failed: {str(e)}")

    return ResponseEnvelope(
        success=True,
        message=f"PDP geometry analysis completed with status: {geom_run.status}",
        data=PDPGeometryResponse.model_validate(geom_run),
    )

@router.get(
    "/{inspection_id}/images/{image_id}/geometry",
    response_model=ResponseEnvelope[PDPGeometryListResponse],
    summary="Retrieve historical PDP geometry analyses",
    description="Retrieve all historical PDP geometry analyses performed on a package surface image.",
)
async def get_pdp_geometry_history(
    inspection_id: uuid.UUID,
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    geometry_service: PDPGeometryService = Depends(get_pdp_geometry_service),
):
    """Retrieve historical PDP geometry analyses."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    _verify_inspection_access(inspection, current_user)

    s_res = await db.execute(
        select(InspectionSurface).where(
            InspectionSurface.inspection_id == inspection_id,
            InspectionSurface.id == image_id,
        )
    )
    surface = s_res.scalar_one_or_none()
    if not surface:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found for this inspection")

    analyses = await geometry_service.get_pdp_geometry_for_surface(db, surface.id)

    return ResponseEnvelope(
        success=True,
        data=PDPGeometryListResponse(
            surface_id=image_id,
            total_analyses=len(analyses),
            analyses=[PDPGeometryResponse.model_validate(a) for a in analyses],
        ),
    )

# ----------------------------------------------------------------------
# PHASE 5: DETERMINISTIC LEGAL METROLOGY COMPLIANCE RULE ENGINE
# ----------------------------------------------------------------------

@router.post(
    "/{inspection_id}/rules/evaluate",
    response_model=ResponseEnvelope[InspectionComplianceSummaryResponse],
    summary="Evaluate deterministic legal compliance rules for an inspection",
    description=(
        "Executes the deterministic Legal Metrology rule engine against the inspection's "
        "structured observations, evidence, and PDP geometry. Evaluates rule applicability "
        "separately from compliance, supports multi-version legal provisions, ensures explainability, "
        "and creates an immutable append-only audit trail. AI/OCR assists perception; this endpoint "
        "alone produces definitive legal verdicts (PASS / FAIL / REVIEW / INDETERMINATE / NOT_APPLICABLE)."
    ),
)
async def evaluate_inspection_rules(
    inspection_id: uuid.UUID,
    request: Optional[RuleEvaluationRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    rule_engine: DeterministicRuleEngine = Depends(get_rule_engine_service),
):
    """Execute deterministic compliance evaluation for an inspection."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    _verify_inspection_access(inspection, current_user)

    rule_set_version = request.rule_set_version if request else None
    rule_codes = request.rule_codes if request else None
    include_test_rules = request.include_test_rules if request else False

    try:
        summary = await rule_engine.evaluate_inspection(
            db=db,
            inspection=inspection,
            rule_set_version=rule_set_version,
            rule_codes=rule_codes,
            include_test_rules=include_test_rules,
            actor_id=current_user.id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deterministic rule evaluation failed: {str(e)}"
        )

    # Convert evaluation results to response schema
    eval_reads: List[RuleEvaluationRead] = []
    for r in summary.evaluations:
        eval_reads.append(
            RuleEvaluationRead(
                id=uuid.uuid4(),
                inspection_id=inspection_id,
                rule_definition_id=r.rule_definition_id,
                outcome=r.outcome,
                legal_rationale=r.legal_rationale,
                statutory_citation=r.statutory_citation,
                rule_code=r.rule_code,
                rule_version=r.rule_version,
                evidence_references=r.evidence_references,
                applicability_result=r.applicability_result,
                evaluation_run_id=summary.evaluation_run_id,
                officer_overridden=False,
                evaluated_at=r.evaluated_at,
            )
        )

    return ResponseEnvelope(
        success=True,
        message=(
            f"Deterministic legal evaluation completed: {summary.pass_count} PASS, "
            f"{summary.fail_count} FAIL, {summary.review_count} REVIEW, "
            f"{summary.indeterminate_count} INDETERMINATE, {summary.not_applicable_count} NOT_APPLICABLE"
        ),
        data=InspectionComplianceSummaryResponse(
            inspection_id=summary.inspection_id,
            evaluation_run_id=summary.evaluation_run_id,
            evaluated_at=summary.evaluated_at,
            rule_set_version=summary.rule_set_version,
            total_rules=summary.total_rules,
            pass_count=summary.pass_count,
            fail_count=summary.fail_count,
            review_count=summary.review_count,
            indeterminate_count=summary.indeterminate_count,
            not_applicable_count=summary.not_applicable_count,
            overall_verdict=summary.overall_verdict,
            evaluations=eval_reads,
        )
    )

@router.get(
    "/{inspection_id}/rules/evaluations",
    response_model=ResponseEnvelope[List[RuleEvaluationRead]],
    summary="Retrieve historical rule evaluations for an inspection",
    description="Retrieve all historical deterministic rule evaluations recorded for an inspection.",
)
async def get_inspection_rule_evaluations(
    inspection_id: uuid.UUID,
    evaluation_run_id: Optional[uuid.UUID] = Query(None),
    latest_only: bool = Query(False, description="If True, return evaluations only from the latest evaluation run"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve historical rule evaluations for an inspection."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    _verify_inspection_access(inspection, current_user)

    query = (
        select(RuleEvaluation)
        .options(selectinload(RuleEvaluation.rule_definition))
        .where(RuleEvaluation.inspection_id == inspection_id)
    )
    if evaluation_run_id:
        query = query.where(RuleEvaluation.evaluation_run_id == evaluation_run_id)
    elif latest_only:
        latest_run_stmt = (
            select(RuleEvaluation.evaluation_run_id)
            .where(RuleEvaluation.inspection_id == inspection_id)
            .order_by(RuleEvaluation.evaluated_at.desc())
            .limit(1)
        )
        latest_run_res = await db.execute(latest_run_stmt)
        latest_eval_run_id = latest_run_res.scalar_one_or_none()
        if latest_eval_run_id:
            query = query.where(RuleEvaluation.evaluation_run_id == latest_eval_run_id)

    eval_res = await db.execute(query.order_by(RuleEvaluation.evaluated_at.desc()))
    evaluations = eval_res.scalars().all()

    return ResponseEnvelope(
        success=True,
        data=[RuleEvaluationRead.model_validate(e) for e in evaluations]
    )

@router.get(
    "/{inspection_id}/rules/evaluations/{evaluation_id}",
    response_model=ResponseEnvelope[RuleEvaluationRead],
    summary="Retrieve detailed view of a single rule evaluation",
    description="Retrieve one detailed rule evaluation record with statutory citation, explanation, evidence, and rule definition.",
)
async def get_single_rule_evaluation(
    inspection_id: uuid.UUID,
    evaluation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve detailed view of a single rule evaluation."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    _verify_inspection_access(inspection, current_user)

    query = (
        select(RuleEvaluation)
        .options(selectinload(RuleEvaluation.rule_definition))
        .where(
            RuleEvaluation.inspection_id == inspection_id,
            RuleEvaluation.id == evaluation_id,
        )
    )
    eval_res = await db.execute(query)
    rule_eval = eval_res.scalar_one_or_none()
    if not rule_eval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule evaluation record not found")

    return ResponseEnvelope(
        success=True,
        data=RuleEvaluationRead.model_validate(rule_eval)
    )


# =========================================================================
# PHASE 6: EVIDENCE & REPORT ENDPOINTS
# =========================================================================

@router.post(
    "/{inspection_id}/reports",
    response_model=ResponseEnvelope[ReportRead],
    status_code=status.HTTP_201_CREATED,
    summary="Generate explainable PDF inspection dossier",
    description="Generate a tamper-evident, explainable PDF dossier from an immutable evidence snapshot.",
)
async def generate_inspection_report(
    inspection_id: uuid.UUID,
    request_body: Optional[ReportGenerateRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage_service: BaseStorageService = Depends(get_storage_service),
    evidence_service: EvidenceService = Depends(get_evidence_service),
    pdf_generator: DossierPDFGenerator = Depends(get_pdf_generator),
):
    """Generate a tamper-evident, explainable PDF dossier from an immutable evidence snapshot."""
    req = request_body or ReportGenerateRequest()

    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    _verify_inspection_access(inspection, current_user)

    # Halt dossier generation if any entity parsing runs failed (Requirement 4)
    failed_entity_runs = await db.execute(
        select(EntityParsingRun)
        .where(
            EntityParsingRun.inspection_id == inspection_id,
            EntityParsingRun.status == "FAILED",
        )
    )
    if failed_entity_runs.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate inspection dossier: One or more entity parsing runs failed. Downstream dossier generation halted.",
        )



    # 1. Determine or create EvidenceSnapshot
    snapshot: Optional[EvidenceSnapshot] = None
    if req.evidence_snapshot_id:
        snap_res = await db.execute(
            select(EvidenceSnapshot).where(
                EvidenceSnapshot.id == req.evidence_snapshot_id,
                EvidenceSnapshot.inspection_id == inspection_id,
            )
        )
        snapshot = snap_res.scalar_one_or_none()
        if not snapshot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified EvidenceSnapshot not found")
    else:
        snapshot = await evidence_service.create_evidence_snapshot(
            db=db,
            inspection_id=inspection_id,
            evaluation_run_id=req.evaluation_run_id,
            created_by_id=current_user.id,
        )

    # 2. Determine sequential report version
    ver_res = await db.execute(
        select(func.max(InspectionReport.report_version)).where(InspectionReport.inspection_id == inspection_id)
    )
    current_max_ver = ver_res.scalar() or 0
    next_report_version = current_max_ver + 1

    # 3. Load full inspection dataset for rendering
    (
        insp,
        surfaces,
        ocr_runs,
        observations,
        geometries,
        evaluations,
        audit_logs,
    ) = await evidence_service.load_inspection_dataset(
        db, inspection_id, evaluation_run_id=snapshot.evaluation_run_id
    )

    dossier_id = uuid.uuid4()
    options = DossierOptions(
        include_images=req.include_images,
        include_ocr_dump=req.include_ocr_dump,
    )

    # 4. Generate PDF bytes and cryptographic SHA-256 seal
    dossier_result = await pdf_generator.generate_dossier(
        inspection=insp,
        surfaces=surfaces,
        ocr_runs=ocr_runs,
        observations=observations,
        geometries=geometries,
        evaluations=evaluations,
        audit_logs=audit_logs,
        snapshot=snapshot,
        dossier_id=dossier_id,
        report_version=next_report_version,
        options=options,
    )

    # 5. Persist PDF to storage abstraction: inspections/{id}/reports/{dossier_id}.pdf
    storage_path = storage_service.build_inspection_path_reference(
        inspection_id=inspection_id,
        subfolder="reports",
        filename=f"{dossier_id}.pdf",
    )
    await storage_service.store(storage_path, dossier_result.pdf_bytes)

    # 6. Save InspectionReport database entity
    report = InspectionReport(
        id=dossier_id,
        inspection_id=inspection_id,
        evidence_snapshot_id=snapshot.id,
        evaluation_run_id=snapshot.evaluation_run_id,
        report_version=next_report_version,
        storage_path=storage_path,
        sha256_hash=dossier_result.sha256_hash,
        file_size_bytes=dossier_result.file_size_bytes,
        status="GENERATED",
        generated_by_id=current_user.id,
        generated_at=datetime.now(timezone.utc),
        metadata_json={
            "rules_count": len(evaluations),
            "surfaces_count": len(surfaces),
            "observations_count": len(observations),
            "integrity_hash": snapshot.integrity_hash,
        },
    )
    db.add(report)

    # 7. Tamper-evident AuditLog entry
    audit_entry = AuditLog(
        inspection_id=inspection_id,
        user_id=current_user.id,
        action="DOSSIER_REPORT_GENERATED",
        entity_type="InspectionReport",
        entity_id=str(dossier_id),
        previous_state={},
        new_state={
            "dossier_id": str(dossier_id),
            "report_version": next_report_version,
            "sha256_hash": dossier_result.sha256_hash,
            "snapshot_id": str(snapshot.id),
        },
        justification=f"Generated version {next_report_version} explainable PDF dossier with SHA-256 seal {dossier_result.sha256_hash}",
    )
    db.add(audit_entry)

    await db.commit()
    await db.refresh(report)

    return ResponseEnvelope(
        success=True,
        data=ReportRead.model_validate(report),
    )

@router.get(
    "/{inspection_id}/reports",
    response_model=ResponseEnvelope[List[ReportRead]],
    summary="List historical reports for an inspection",
    description="Retrieve list of all historical PDF dossier reports generated for an inspection.",
)
async def list_inspection_reports(
    inspection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve list of all historical PDF dossier reports generated for an inspection."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    _verify_inspection_access(inspection, current_user)

    stmt = (
        select(InspectionReport)
        .where(InspectionReport.inspection_id == inspection_id)
        .order_by(InspectionReport.report_version.desc())
    )
    rep_res = await db.execute(stmt)
    reports = rep_res.scalars().all()

    return ResponseEnvelope(
        success=True,
        data=[ReportRead.model_validate(r) for r in reports],
    )

@router.get(
    "/{inspection_id}/reports/{report_id}",
    response_model=ResponseEnvelope[ReportRead],
    summary="Retrieve inspection report metadata",
    description="Retrieve metadata for a specific generated PDF dossier report.",
)
async def get_inspection_report(
    inspection_id: uuid.UUID,
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve metadata for a specific generated PDF dossier report."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    _verify_inspection_access(inspection, current_user)

    stmt = select(InspectionReport).where(
        InspectionReport.inspection_id == inspection_id,
        InspectionReport.id == report_id,
    )
    rep_res = await db.execute(stmt)
    report = rep_res.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection report not found")

    return ResponseEnvelope(
        success=True,
        data=ReportRead.model_validate(report),
    )

@router.get(
    "/{inspection_id}/reports/{report_id}/content",
    summary="Download or stream generated PDF dossier",
    description="Stream the raw bytes of the generated PDF dossier with proper application/pdf Content-Type.",
)
async def get_inspection_report_content(
    inspection_id: uuid.UUID,
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage_service: BaseStorageService = Depends(get_storage_service),
):
    """Stream the raw bytes of the generated PDF dossier."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    _verify_inspection_access(inspection, current_user)

    stmt = select(InspectionReport).where(
        InspectionReport.inspection_id == inspection_id,
        InspectionReport.id == report_id,
    )
    rep_res = await db.execute(stmt)
    report = rep_res.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection report not found")

    try:
        pdf_bytes = await storage_service.retrieve(report.storage_path)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF content file not found on storage")

    filename = f"dossier_{inspection.inspection_number}_v{report.report_version}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "X-Dossier-ID": str(report.id),
            "X-SHA256-Hash": report.sha256_hash,
        },
    )

@router.get(
    "/{inspection_id}/evidence",
    response_model=ResponseEnvelope[EvidenceBundleResponse],
    summary="Retrieve evidence bundle and manifest metadata",
    description="Retrieve machine-readable evidence bundle containing all perceptions, observations, geometries, and evaluations.",
)
async def get_inspection_evidence_bundle(
    inspection_id: uuid.UUID,
    snapshot_id: Optional[uuid.UUID] = Query(None),
    evaluation_run_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    evidence_service: EvidenceService = Depends(get_evidence_service),
):
    """Retrieve machine-readable evidence bundle."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    _verify_inspection_access(inspection, current_user)

    if snapshot_id:
        snap_res = await db.execute(
            select(EvidenceSnapshot).where(
                EvidenceSnapshot.id == snapshot_id,
                EvidenceSnapshot.inspection_id == inspection_id,
            )
        )
        snapshot = snap_res.scalar_one_or_none()
        if not snapshot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EvidenceSnapshot not found")
        return ResponseEnvelope(
            success=True,
            data=EvidenceBundleResponse(
                manifest=snapshot.manifest_json,
                integrity_hash=snapshot.integrity_hash,
                snapshot_id=snapshot.id,
                graph=snapshot.manifest_json.get("graph"),
            ),
        )

    # Otherwise build fresh active manifest
    insp, surfaces, ocr_runs, observations, geometries, evaluations, audit_logs = (
        await evidence_service.load_inspection_dataset(db, inspection_id, evaluation_run_id)
    )
    manifest = EvidenceBundleBuilder.build_manifest(
        inspection=insp,
        surfaces=surfaces,
        ocr_runs=ocr_runs,
        observations=observations,
        geometries=geometries,
        evaluations=evaluations,
        audit_logs=audit_logs,
        evaluation_run_id=evaluation_run_id,
    )
    manifest_dict = manifest.model_dump()
    integrity_hash = calculate_canonical_json_sha256(manifest_dict)
    adj_res = await db.execute(
        select(OCRAdjudication).where(
            OCRAdjudication.inspection_id == inspection_id,
            OCRAdjudication.is_active == True,
        )
    )
    adjudications = adj_res.scalars().all()

    trace_graph = evidence_service.build_evidence_graph(
        surfaces=surfaces,
        ocr_runs=ocr_runs,
        observations=observations,
        geometries=geometries,
        evaluations=evaluations,
        adjudications=adjudications,
    )

    return ResponseEnvelope(
        success=True,
        data=EvidenceBundleResponse(
            manifest=manifest_dict,
            integrity_hash=integrity_hash,
            snapshot_id=None,
            graph=trace_graph.model_dump(),
        ),
    )

@router.get(
    "/{inspection_id}/evidence/{snapshot_id}",
    response_model=ResponseEnvelope[EvidenceSnapshotRead],
    summary="Retrieve specific immutable evidence snapshot",
    description="Retrieve the metadata and source record mapping of a specific immutable EvidenceSnapshot.",
)
async def get_evidence_snapshot(
    inspection_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve specific immutable evidence snapshot."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    _verify_inspection_access(inspection, current_user)

    snap_res = await db.execute(
        select(EvidenceSnapshot).where(
            EvidenceSnapshot.id == snapshot_id,
            EvidenceSnapshot.inspection_id == inspection_id,
        )
    )
    snapshot = snap_res.scalar_one_or_none()
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EvidenceSnapshot not found")

    return ResponseEnvelope(
        success=True,
        data=EvidenceSnapshotRead.model_validate(snapshot),
    )


