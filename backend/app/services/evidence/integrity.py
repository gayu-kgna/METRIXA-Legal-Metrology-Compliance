import hashlib
import json
from typing import Dict, Any, Union

def calculate_sha256(data: bytes) -> str:
    """Calculate the cryptographic SHA-256 hash of raw byte data."""
    hasher = hashlib.sha256()
    hasher.update(data)
    return hasher.hexdigest().lower()

def calculate_canonical_json_sha256(data: Union[Dict[str, Any], list]) -> str:
    """
    Calculate the deterministic cryptographic SHA-256 hash of a JSON-serializable dictionary or list.
    Enforces canonical sorting of keys and compact separators to ensure reproducible hashes across platforms.
    """
    def _default_serializer(obj):
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        if hasattr(obj, "__str__"):
            return str(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    canonical_json_str = json.dumps(
        data,
        sort_keys=True,
        separators=(',', ':'),
        default=_default_serializer,
        ensure_ascii=True,
    )
    return calculate_sha256(canonical_json_str.encode("utf-8"))

def verify_sha256(data: bytes, expected_hash: str) -> bool:
    """Verify that the SHA-256 hash of raw bytes matches the expected hash."""
    if not expected_hash:
        return False
    actual_hash = calculate_sha256(data)
    return actual_hash == expected_hash.strip().lower()

def verify_canonical_json_sha256(data: Union[Dict[str, Any], list], expected_hash: str) -> bool:
    """Verify that canonical JSON hash matches expected hash."""
    if not expected_hash:
        return False
    actual_hash = calculate_canonical_json_sha256(data)
    return actual_hash == expected_hash.strip().lower()
