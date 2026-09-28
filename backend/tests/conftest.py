import asyncio
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.config import settings
from app.core.database import get_db, Base
from app.core.security import hash_password, create_access_token
from app.models.user import User
from app.models.enums import UserRole

# Use NullPool for tests so connections don't interfere
test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool, echo=False)
TestingSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Yield an isolated database session for setup fixtures."""
    async with TestingSessionLocal() as session:
        yield session

@pytest_asyncio.fixture(scope="function")
async def client():
    """Yield an async test client with per-request database sessions."""
    async def override_get_db():
        async with TestingSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest_asyncio.fixture(scope="function")
async def test_inspector(db_session: AsyncSession) -> User:
    """Create and return a persistent test inspector."""
    email = f"inspector_{uuid.uuid4().hex[:8]}@metrixa.gov.in"
    inspector = User(
        email=email,
        hashed_password=hash_password("InspectorPass123!"),
        full_name="Officer Ramesh Kumar",
        role=UserRole.INSPECTOR,
        badge_number="LM-DEL-104",
        jurisdiction="South Delhi",
        is_active=True,
    )
    db_session.add(inspector)
    await db_session.commit()
    await db_session.refresh(inspector)
    return inspector

@pytest_asyncio.fixture(scope="function")
async def test_adjudicator(db_session: AsyncSession) -> User:
    """Create and return a persistent test senior adjudicator."""
    email = f"adjudicator_{uuid.uuid4().hex[:8]}@metrixa.gov.in"
    adjudicator = User(
        email=email,
        hashed_password=hash_password("AdjudicatorPass123!"),
        full_name="Senior Officer Sunita Verma",
        role=UserRole.ADJUDICATOR,
        badge_number="LM-HQ-002",
        jurisdiction="National Headquarters",
        is_active=True,
    )
    db_session.add(adjudicator)
    await db_session.commit()
    await db_session.refresh(adjudicator)
    return adjudicator

@pytest_asyncio.fixture(scope="function")
def inspector_token(test_inspector: User) -> str:
    return create_access_token({"sub": str(test_inspector.id), "email": test_inspector.email, "role": test_inspector.role.value})

@pytest_asyncio.fixture(scope="function")
def adjudicator_token(test_adjudicator: User) -> str:
    return create_access_token({"sub": str(test_adjudicator.id), "email": test_adjudicator.email, "role": test_adjudicator.role.value})

@pytest_asyncio.fixture(scope="function")
def auth_headers(inspector_token: str) -> dict:
    return {"Authorization": f"Bearer {inspector_token}"}
