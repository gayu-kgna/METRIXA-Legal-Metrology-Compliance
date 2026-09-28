import io
import uuid
import hashlib
import pytest
from PIL import Image
from httpx import AsyncClient

def generate_image_bytes(format: str = "JPEG", size=(200, 200), color=(200, 50, 50)) -> bytes:
    """Helper to synthesize valid in-memory image bytes."""
    bio = io.BytesIO()
    mode = "RGB" if format.upper() in ("JPEG", "JPG") else "RGBA"
    img = Image.new(mode, size, color)
    img.save(bio, format=format)
    return bio.getvalue()

@pytest.mark.asyncio
async def test_supported_formats_upload(client: AsyncClient, inspector_token: str):
    """Verify JPEG, PNG, and WEBP uploads succeed with correct MIME and format extraction."""
    headers = {"Authorization": f"Bearer {inspector_token}"}

    # 1. Create Inspection
    ins_resp = await client.post("/api/v1/inspections", json={"retail_outlet_name": "Test Formats Store"}, headers=headers)
    assert ins_resp.status_code == 201
    ins_id = ins_resp.json()["data"]["id"]

    test_formats = [
        ("JPEG", "image/jpeg", "front.jpg"),
        ("PNG", "image/png", "back.png"),
        ("WEBP", "image/webp", "side.webp"),
    ]

    for fmt, expected_mime, filename in test_formats:
        img_bytes = generate_image_bytes(format=fmt, size=(300, 400))
        sha256 = hashlib.sha256(img_bytes).hexdigest()

        files = {"file": (filename, img_bytes, expected_mime)}
        upload_resp = await client.post(
            f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images",
            files=files,
            headers=headers
        )
        assert upload_resp.status_code == 201
        data = upload_resp.json()["data"]
        assert data["detected_format"] == ("JPEG" if fmt == "JPEG" else fmt)
        assert data["mime_type"] == expected_mime
        assert data["image_width"] == 300
        assert data["image_height"] == 400
        assert data["file_size_bytes"] == len(img_bytes)
        assert data["sha256_hash"] == sha256
        assert "storage" not in data["storage_reference"] or "inspections/" in data["storage_reference"]
        # Ensure no absolute paths exposed
        assert "C:" not in data["storage_reference"]
        assert "\\" not in data["storage_reference"]

@pytest.mark.asyncio
async def test_invalid_uploads_rejected(client: AsyncClient, inspector_token: str):
    """Verify corrupted, non-image, empty, and dimension-violating uploads are cleanly rejected with 400."""
    headers = {"Authorization": f"Bearer {inspector_token}"}
    ins_resp = await client.post("/api/v1/inspections", json={"retail_outlet_name": "Validation Test Store"}, headers=headers)
    ins_id = ins_resp.json()["data"]["id"]

    # 1. Empty upload (0 bytes)
    resp = await client.post(
        f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
        headers=headers
    )
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()

    # 2. Non-image plain text file
    resp = await client.post(
        f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images",
        files={"file": ("malicious.txt", b"Hello this is not an image", "text/plain")},
        headers=headers
    )
    assert resp.status_code == 400
    assert "corrupted" in resp.json()["detail"].lower() or "invalid" in resp.json()["detail"].lower()

    # 3. Corrupted header
    corrupted_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"random_corrupted_garbage_bytes_12345"
    resp = await client.post(
        f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images",
        files={"file": ("corrupt.jpg", corrupted_bytes, "image/jpeg")},
        headers=headers
    )
    assert resp.status_code == 400
    assert "corrupted" in resp.json()["detail"].lower() or "invalid" in resp.json()["detail"].lower()

    # 4. Dimension too small (under 10x10 px limit)
    tiny_bytes = generate_image_bytes(format="PNG", size=(5, 5))
    resp = await client.post(
        f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images",
        files={"file": ("tiny.png", tiny_bytes, "image/png")},
        headers=headers
    )
    assert resp.status_code == 400
    assert "dimensions" in resp.json()["detail"].lower()

    # 5. Invalid surface type in URL path
    valid_bytes = generate_image_bytes(format="JPEG", size=(100, 100))
    resp = await client.post(
        f"/api/v1/inspections/{ins_id}/surfaces/INVALID_SURFACE/images",
        files={"file": ("valid.jpg", valid_bytes, "image/jpeg")},
        headers=headers
    )
    assert resp.status_code == 422  # Enum validation failure

@pytest.mark.asyncio
async def test_six_package_surfaces_support(client: AsyncClient, inspector_token: str):
    """Verify all 6 standardized package surfaces are supported."""
    headers = {"Authorization": f"Bearer {inspector_token}"}
    ins_resp = await client.post("/api/v1/inspections", json={"retail_outlet_name": "Six Surface Store"}, headers=headers)
    ins_id = ins_resp.json()["data"]["id"]

    surfaces = ["FRONT_PDP", "BACK", "LEFT", "RIGHT", "TOP", "BOTTOM"]
    for s_type in surfaces:
        img_bytes = generate_image_bytes(format="JPEG", size=(150, 150))
        resp = await client.post(
            f"/api/v1/inspections/{ins_id}/surfaces/{s_type}/images",
            files={"file": (f"{s_type.lower()}.jpg", img_bytes, "image/jpeg")},
            headers=headers
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["surface_type"] == s_type

    # Verify listing per surface returns the uploaded image
    for s_type in surfaces:
        list_resp = await client.get(
            f"/api/v1/inspections/{ins_id}/surfaces/{s_type}/images",
            headers=headers
        )
        assert list_resp.status_code == 200
        items = list_resp.json()["data"]
        assert len(items) == 1
        assert items[0]["surface_type"] == s_type

@pytest.mark.asyncio
async def test_multiple_images_per_surface(client: AsyncClient, inspector_token: str):
    """Verify multiple images can be associated with the same surface (e.g. FRONT_PDP)."""
    headers = {"Authorization": f"Bearer {inspector_token}"}
    ins_resp = await client.post("/api/v1/inspections", json={"retail_outlet_name": "Multi Image Store"}, headers=headers)
    ins_id = ins_resp.json()["data"]["id"]

    # Upload 2 different captures of FRONT_PDP
    img1 = generate_image_bytes(format="JPEG", size=(200, 200), color=(100, 100, 200))
    img2 = generate_image_bytes(format="JPEG", size=(250, 250), color=(200, 100, 100))

    resp1 = await client.post(
        f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images",
        files={"file": ("capture1.jpg", img1, "image/jpeg")},
        headers=headers
    )
    assert resp1.status_code == 201

    resp2 = await client.post(
        f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images",
        files={"file": ("capture2.jpg", img2, "image/jpeg")},
        headers=headers
    )
    assert resp2.status_code == 201

    # List FRONT_PDP images: both must exist
    list_resp = await client.get(
        f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images",
        headers=headers
    )
    assert list_resp.status_code == 200
    images = list_resp.json()["data"]
    assert len(images) == 2

@pytest.mark.asyncio
async def test_duplicate_content_detection(client: AsyncClient, inspector_token: str):
    """
    Verify duplicate content is detected via SHA-256 without rejecting or overwriting.
    Allows legitimate duplicate images across surfaces and inspections.
    """
    headers = {"Authorization": f"Bearer {inspector_token}"}

    ins1_resp = await client.post("/api/v1/inspections", json={"retail_outlet_name": "Store Alpha"}, headers=headers)
    ins1_id = ins1_resp.json()["data"]["id"]

    ins2_resp = await client.post("/api/v1/inspections", json={"retail_outlet_name": "Store Beta"}, headers=headers)
    ins2_id = ins2_resp.json()["data"]["id"]

    # Use randomized color to ensure unique SHA-256 per test run against persistent test DB
    salt = uuid.uuid4().bytes
    identical_bytes = generate_image_bytes(format="JPEG", size=(220, 220), color=(salt[0], salt[1], salt[2]))
    sha256 = hashlib.sha256(identical_bytes).hexdigest()

    # First upload: not a duplicate
    upload1 = await client.post(
        f"/api/v1/inspections/{ins1_id}/surfaces/FRONT_PDP/images",
        files={"file": ("original_pack.jpg", identical_bytes, "image/jpeg")},
        headers=headers
    )
    assert upload1.status_code == 201
    data1 = upload1.json()["data"]
    assert data1["is_duplicate"] is False
    assert data1["duplicate_of_surface_id"] is None
    first_id = data1["id"]

    # Second upload to another inspection: identical bytes detected as duplicate!
    upload2 = await client.post(
        f"/api/v1/inspections/{ins2_id}/surfaces/FRONT_PDP/images",
        files={"file": ("reupload_pack.jpg", identical_bytes, "image/jpeg")},
        headers=headers
    )
    assert upload2.status_code == 201
    data2 = upload2.json()["data"]
    assert data2["is_duplicate"] is True
    assert data2["duplicate_of_surface_id"] == first_id
    assert data2["sha256_hash"] == sha256
    # Original image in ins1 was NOT overwritten
    assert data2["id"] != first_id

@pytest.mark.asyncio
async def test_security_and_authorization(
    client: AsyncClient,
    inspector_token: str,
    test_inspector,
    db_session
):
    """Verify unauthenticated, unauthorized, and path-traversal attacks are blocked."""
    # 1. Unauthenticated request rejected
    resp = await client.post(
        f"/api/v1/inspections/{uuid.uuid4()}/surfaces/FRONT_PDP/images",
        files={"file": ("test.jpg", b"dummy", "image/jpeg")}
    )
    assert resp.status_code == 401

    # 2. Inspector A creates inspection
    headers_a = {"Authorization": f"Bearer {inspector_token}"}
    ins_resp = await client.post("/api/v1/inspections", json={"retail_outlet_name": "Inspector A Store"}, headers=headers_a)
    ins_id = ins_resp.json()["data"]["id"]

    # 3. Inspector B tries to upload to Inspector A's inspection -> 403 Forbidden
    from app.models.user import User
    from app.models.enums import UserRole
    from app.core.security import hash_password, create_access_token

    inspector_b = User(
        email=f"inspector_b_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Officer Bob",
        role=UserRole.INSPECTOR,
        is_active=True
    )
    db_session.add(inspector_b)
    await db_session.commit()
    await db_session.refresh(inspector_b)
    token_b = create_access_token({"sub": str(inspector_b.id), "email": inspector_b.email, "role": inspector_b.role.value})
    headers_b = {"Authorization": f"Bearer {token_b}"}

    img_bytes = generate_image_bytes(format="JPEG")
    unauth_resp = await client.post(
        f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images",
        files={"file": ("hack.jpg", img_bytes, "image/jpeg")},
        headers=headers_b
    )
    assert unauth_resp.status_code == 403
    assert "forbidden" in unauth_resp.json()["detail"].lower()

    # 4. Path traversal in original filename safely sanitized
    traversal_resp = await client.post(
        f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images",
        files={"file": ("../../../../etc/passwd.jpg", img_bytes, "image/jpeg")},
        headers=headers_a
    )
    assert traversal_resp.status_code == 201
    stored_name = traversal_resp.json()["data"]["original_filename"]
    assert ".." not in stored_name
    assert "/" not in stored_name
    assert "\\" not in stored_name

@pytest.mark.asyncio
async def test_end_to_end_image_pipeline(client: AsyncClient, inspector_token: str):
    """
    Complete End-to-End Phase 2 Integration Test:
    Product -> Inspection -> Upload -> Hash -> Store -> Metadata -> Content Retrieval -> Exact Byte Match.
    """
    headers = {"Authorization": f"Bearer {inspector_token}"}

    # 1. Create Product
    prod_resp = await client.post("/api/v1/products", json={
        "brand_name": "Amul",
        "product_name": "Taaza Fresh Toned Milk 1L",
        "category": "Dairy",
        "commodity_type": "Milk"
    }, headers=headers)
    assert prod_resp.status_code == 201
    prod_id = prod_resp.json()["data"]["id"]

    # 2. Create Inspection
    ins_resp = await client.post("/api/v1/inspections", json={
        "product_id": prod_id,
        "retail_outlet_name": "Mother Dairy Booth Laxmi Nagar",
        "retail_outlet_address": "Main Market, Laxmi Nagar, Delhi",
    }, headers=headers)
    assert ins_resp.status_code == 201
    ins_id = ins_resp.json()["data"]["id"]

    # 3. Upload Image to FRONT_PDP with unique random color per test run
    salt = uuid.uuid4().bytes
    original_bytes = generate_image_bytes(format="JPEG", size=(640, 480), color=(salt[0], salt[1], salt[2]))
    original_sha256 = hashlib.sha256(original_bytes).hexdigest()

    upload_resp = await client.post(
        f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images",
        files={"file": ("amul_taaza_front.jpg", original_bytes, "image/jpeg")},
        headers=headers
    )
    assert upload_resp.status_code == 201
    upload_data = upload_resp.json()["data"]
    image_id = upload_data["id"]
    assert upload_data["sha256_hash"] == original_sha256
    assert upload_data["image_width"] == 640
    assert upload_data["image_height"] == 480

    # 4. Retrieve Image Metadata via GET
    meta_resp = await client.get(f"/api/v1/inspections/{ins_id}/images/{image_id}", headers=headers)
    assert meta_resp.status_code == 200
    meta = meta_resp.json()["data"]
    assert meta["id"] == image_id
    assert meta["sha256_hash"] == original_sha256

    # 5. Retrieve Original Raw Bytes via Content Endpoint
    content_resp = await client.get(f"/api/v1/inspections/{ins_id}/images/{image_id}/content", headers=headers)
    assert content_resp.status_code == 200
    retrieved_bytes = content_resp.content

    # 6. CRITICAL VERIFICATION: Exact byte-level equality!
    assert retrieved_bytes == original_bytes
    assert hashlib.sha256(retrieved_bytes).hexdigest() == original_sha256
    assert content_resp.headers["X-Content-SHA256"] == original_sha256
    assert content_resp.headers["Content-Type"] == "image/jpeg"
