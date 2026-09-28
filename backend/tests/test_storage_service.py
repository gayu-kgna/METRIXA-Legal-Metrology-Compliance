import uuid
import pytest
import pytest_asyncio
from pathlib import Path
from app.services.storage.local import LocalStorageService

@pytest.fixture
def temp_storage(tmp_path: Path) -> LocalStorageService:
    return LocalStorageService(storage_root=tmp_path)

@pytest.mark.asyncio
async def test_local_storage_crud(temp_storage: LocalStorageService):
    """Test standard storage operations: store, retrieve, exists, delete."""
    ref = "inspections/test-123/original/sample.jpg"
    data = b"metrixa_raw_image_bytes_verification"

    # Store
    persisted_ref = await temp_storage.store(ref, data)
    assert persisted_ref == ref

    # Exists
    assert await temp_storage.exists(ref) is True
    assert await temp_storage.exists("non_existent.jpg") is False

    # Retrieve
    retrieved = await temp_storage.retrieve(ref)
    assert retrieved == data

    # Delete
    deleted = await temp_storage.delete(ref)
    assert deleted is True
    assert await temp_storage.exists(ref) is False

@pytest.mark.asyncio
async def test_local_storage_path_traversal_defense(temp_storage: LocalStorageService):
    """Test that path traversal attempts are detected and strictly rejected."""
    traversal_refs = [
        "../../etc/passwd",
        "inspections/../../../windows/system32/cmd.exe",
        "../secret.txt",
        "/absolute/path/attempt.jpg",
    ]

    for malicious_ref in traversal_refs:
        # Should raise ValueError and NEVER escape the sandbox
        with pytest.raises(ValueError, match="Security violation"):
            await temp_storage.store(malicious_ref, b"attack")

        with pytest.raises(ValueError, match="Security violation"):
            await temp_storage.retrieve(malicious_ref)

def test_build_inspection_path_reference(temp_storage: LocalStorageService):
    """Test normalized reference construction and sanitization."""
    insp_id = uuid.uuid4()
    ref = temp_storage.build_inspection_path_reference(
        inspection_id=insp_id,
        subfolder="original",
        filename="../../escape.jpg"
    )
    # The helper strips directory navigation
    assert ref == f"inspections/{insp_id}/original/escape.jpg"
    assert ".." not in ref
