from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import engine
from app.api.v1.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify database connection
    try:
        async with engine.connect() as conn:
            pass
    except Exception as e:
        print(f"[METRIXA WARNING] Database connection issue on startup: {e}")
    yield
    # Shutdown: dispose database pool
    await engine.dispose()

app = FastAPI(
    title=f"{settings.PROJECT_NAME} — {settings.PROJECT_DESCRIPTION}",
    description=(
        f"**Metrixa** is an intelligent inspection platform designed to assess compliance "
        f"of packaged commodities under the **{settings.LEGAL_FRAMEWORK}**.\n\n"
        f"**Architectural Principles:**\n"
        f"- Strict separation of AI perception and deterministic legal decision making.\n"
        f"- Product identity persistent across multiple point-in-time inspections.\n"
        f"- Tamper-evident evidence packages with cryptographic hashing (SHA-256).\n"
        f"- Immutable observation revisions to prevent silent record overwrite.\n"
        f"- Declarative, versioned statutory rule definitions."
    ),
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*", "X-Dossier-ID", "X-SHA256-Hash", "Content-Disposition"],
)

# Mount central API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["Root"])
async def root():
    return {
        "platform": settings.PROJECT_NAME,
        "description": settings.PROJECT_DESCRIPTION,
        "legal_framework": settings.LEGAL_FRAMEWORK,
        "version": settings.VERSION,
        "docs_url": f"{settings.API_V1_STR}/docs",
        "openapi_url": f"{settings.API_V1_STR}/openapi.json",
    }

@app.get("/health", tags=["Health"])
async def root_health():
    """Top-level health check endpoint for cloud orchestrators and load balancers."""
    return {
        "status": "healthy",
        "platform": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION,
    }

