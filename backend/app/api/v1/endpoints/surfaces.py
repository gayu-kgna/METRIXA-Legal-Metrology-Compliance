import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.inspection import Inspection
from app.models.surface import InspectionSurface
from app.models.ocr_region import OCRRegion
from app.models.evidence import EvidenceItem
from app.models.user import User
from app.schemas.surface import SurfaceCreate, SurfaceRead, OCRRegionBase, OCRRegionCreate, OCRRegionRead
from app.schemas.evidence import EvidenceItemBase, EvidenceItemCreate, EvidenceItemRead
from app.schemas.common import ResponseEnvelope
from app.api.deps import get_current_user

router = APIRouter()

@router.post("", response_model=ResponseEnvelope[SurfaceRead], status_code=status.HTTP_201_CREATED)
async def register_surface(
    surface_in: SurfaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Register a package surface image with cryptographic SHA-256 hash
    and quality metrics (blur score, glare ratio).
    """
    ins = await db.execute(select(Inspection).where(Inspection.id == surface_in.inspection_id))
    if not ins.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    surface = InspectionSurface(**surface_in.model_dump())
    db.add(surface)
    await db.commit()
    await db.refresh(surface)
    return ResponseEnvelope(
        success=True,
        message="Surface registered",
        data=SurfaceRead.model_validate(surface)
    )

@router.get("/{surface_id}", response_model=ResponseEnvelope[SurfaceRead])
async def get_surface(
    surface_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve package surface details."""
    result = await db.execute(select(InspectionSurface).where(InspectionSurface.id == surface_id))
    surface = result.scalar_one_or_none()
    if not surface:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Surface not found")
    return ResponseEnvelope(success=True, data=SurfaceRead.model_validate(surface))

@router.post("/{surface_id}/ocr-regions", response_model=ResponseEnvelope[List[OCRRegionRead]], status_code=status.HTTP_201_CREATED)
async def register_ocr_regions(
    surface_id: uuid.UUID,
    regions_in: List[OCRRegionBase],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Register extracted OCR tokens with normalized bounding boxes [ymin, xmin, ymax, xmax].
    """
    s_res = await db.execute(select(InspectionSurface).where(InspectionSurface.id == surface_id))
    if not s_res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Surface not found")

    created_regions = []
    for reg_data in regions_in:
        ocr_reg = OCRRegion(surface_id=surface_id, **reg_data.model_dump())
        db.add(ocr_reg)
        created_regions.append(ocr_reg)
    
    await db.commit()
    for reg in created_regions:
        await db.refresh(reg)

    return ResponseEnvelope(
        success=True,
        message=f"{len(created_regions)} OCR regions registered",
        data=[OCRRegionRead.model_validate(r) for r in created_regions]
    )

@router.post("/{surface_id}/evidence", response_model=ResponseEnvelope[EvidenceItemRead], status_code=status.HTTP_201_CREATED)
async def register_evidence_item(
    surface_id: uuid.UUID,
    evidence_in: EvidenceItemBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Register a tamper-evident evidence package item (e.g. cropped image slice, cryptographic seal).
    """
    s_res = await db.execute(select(InspectionSurface).where(InspectionSurface.id == surface_id))
    surface = s_res.scalar_one_or_none()
    if not surface:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Surface not found")

    evidence = EvidenceItem(
        inspection_id=surface.inspection_id,
        surface_id=surface_id,
        **evidence_in.model_dump()
    )
    db.add(evidence)
    await db.commit()
    await db.refresh(evidence)
    return ResponseEnvelope(
        success=True,
        message="Evidence item registered",
        data=EvidenceItemRead.model_validate(evidence)
    )
