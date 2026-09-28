from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.analytics import (
    AnalyticsOverview,
    TrendDataPoint,
    OutcomeDistribution,
    CategoryDistributionItem,
    LocationDistributionItem,
    AdjudicationActivityItem,
)
from app.services.analytics.service import (
    get_analytics_overview,
    get_inspections_trend,
    get_outcomes_breakdown,
    get_categories_breakdown,
    get_locations_breakdown,
    get_adjudication_activity,
)

router = APIRouter()

@router.get("/overview", response_model=ResponseEnvelope[AnalyticsOverview])
async def get_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Factual operational counts for dashboard KPI metrics."""
    data = await get_analytics_overview(db)
    return ResponseEnvelope(success=True, data=data)

@router.get("/inspections", response_model=ResponseEnvelope[List[TrendDataPoint]])
async def get_inspections_trend_data(
    days: int = Query(30, ge=7, le=365, description="Number of days for historical trend"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Historical volume of inspections over time."""
    data = await get_inspections_trend(db, days=days)
    return ResponseEnvelope(success=True, data=data)

@router.get("/outcomes", response_model=ResponseEnvelope[OutcomeDistribution])
async def get_outcomes_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Historical rule evaluation outcome counts (PASS, REVIEW, FAIL, UNCERTAIN)."""
    data = await get_outcomes_breakdown(db)
    return ResponseEnvelope(success=True, data=data)

@router.get("/categories", response_model=ResponseEnvelope[List[CategoryDistributionItem]])
async def get_categories_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Historical inspection breakdown across commodity categories."""
    data = await get_categories_breakdown(db)
    return ResponseEnvelope(success=True, data=data)

@router.get("/locations", response_model=ResponseEnvelope[List[LocationDistributionItem]])
async def get_locations_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Historical inspection breakdown across retail outlets and field locations."""
    data = await get_locations_breakdown(db)
    return ResponseEnvelope(success=True, data=data)

@router.get("/adjudications", response_model=ResponseEnvelope[List[AdjudicationActivityItem]])
async def get_adjudications_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Historical human adjudication activity by correction type."""
    data = await get_adjudication_activity(db)
    return ResponseEnvelope(success=True, data=data)
