import uuid
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_user_registration_and_login(client: AsyncClient):
    """Test user registration and JWT token login."""
    unique_email = f"officer_{uuid.uuid4().hex[:8]}@example.com"
    reg_payload = {
        "email": unique_email,
        "password": "SecurePassword123!",
        "full_name": "Inspector Test",
        "role": "INSPECTOR",
        "badge_number": "LM-TEST-01",
        "jurisdiction": "Central Delhi",
    }
    
    reg_resp = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert reg_data["success"] is True
    assert reg_data["data"]["email"] == unique_email

    # Login
    login_payload = {
        "email": unique_email,
        "password": "SecurePassword123!"
    }
    login_resp = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data["data"]
    token = login_data["data"]["access_token"]

    # Verify /me endpoint
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["data"]["email"] == unique_email
