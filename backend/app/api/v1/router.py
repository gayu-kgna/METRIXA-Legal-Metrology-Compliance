from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    auth,
    products,
    inspections,
    surfaces,
    observations,
    rules,
    audit,
    adjudication,
    analytics,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Officers"])
api_router.include_router(products.router, prefix="/products", tags=["Packaged Commodities (Products)"])
api_router.include_router(inspections.router, prefix="/inspections", tags=["Inspections Lifecycle"])
api_router.include_router(adjudication.router, prefix="/inspections", tags=["Inspection Adjudication & Workspace"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Dashboard Analytics & Operational Trends"])
api_router.include_router(surfaces.router, prefix="/surfaces", tags=["Surfaces & Evidence Items"])
api_router.include_router(observations.router, prefix="/observations", tags=["Observations & Adjudication"])
api_router.include_router(rules.router, prefix="/rules", tags=["Versioned Legal Rules & Evaluations"])
api_router.include_router(audit.router, prefix="/audit", tags=["Tamper-Evident Audit Trail"])
