# Metrixa Security Posture & Hardening Policy

> **Objective**: Ensure absolute court admissibility, evidence integrity, non-repudiation, and resilience against adversarial inputs across all inspection touchpoints.

---

## 1. Threat Model & Security Principles

As a government legal enforcement platform, Metrixa is designed to withstand both accidental operational errors and intentional tampering by malicious retail entities or compromised inspectors.

Key design principles:
1. **Zero Evidence Fabrication**: The system never infers, synthesizes, or invents measurements. If physical calibration data is missing, the status is explicitly `UNCALIBRATED` / `INDETERMINATE`.
2. **Immutable Append-Only Audit Trail**: Historical observations and raw images cannot be edited or destroyed through standard application workflows.
3. **Defense in Depth**: Every uploaded asset undergoes magic bytes inspection, dimension checks, storage path sanitization, and cryptographic hashing before database registration.

---

## 2. Authentication & Role-Based Access Control (RBAC)

Metrixa uses cryptographically signed JSON Web Tokens (JWT) using the `HS256` algorithm with distinct role definitions:

| Role | Permitted Actions | Forbidden Actions |
| :--- | :--- | :--- |
| `INSPECTOR` | Create inspections, upload surface imagery, record manual observations, initiate OCR/rules | Cannot adjudicate severe conflicts, cannot override rules |
| `ADJUDICATOR` | All inspector rights, plus review conflicting declarations, approve legal dossiers, override verdicts with rationale | Cannot alter audit log records or erase raw image bytes |
| `ADMIN` | Manage users, view national audit trails, update statutory rule definitions | Cannot retroactively modify finalized inspection reports |
| `PUBLIC` | Verify QR code on formal inspection notices, view certified public summary | Cannot access raw inspection data or inspector badge details |

---

## 3. Production Environment Hardening

Metrixa includes an active environment validator implemented in `app/core/config.py`:
```python
@model_validator(mode="after")
def validate_production_hardening(self) -> "Settings":
    if self.ENVIRONMENT.lower() in ("production", "prod"):
        insecure_dev_secrets = [
            "metrixa_dev_super_secret_jwt_key_sih2026_change_in_production",
            "secret",
            "changeme",
            "insecure-default-change-in-production-only"
        ]
        if self.JWT_SECRET_KEY in insecure_dev_secrets or len(self.JWT_SECRET_KEY) < 32:
            raise ValueError("CRITICAL SECURITY FAILURE: Default or insecure JWT_SECRET_KEY cannot be used in production.")
        if self.DEBUG:
            raise ValueError("CRITICAL SECURITY FAILURE: DEBUG mode must be disabled in production.")
    return self
```
- If `ENVIRONMENT == "production"` and the secret is trivial, insecure, or `< 32` characters, startup aborts immediately.
- In production, `DEBUG` must be `false` to prevent internal stack trace exposure.

---

## 4. Input Validation & File Signature (Magic Bytes) Verification

Relying solely on file extensions (e.g. `.jpg`) allows polyglot exploits, executable masking, and shell uploads. Metrixa enforces multi-stage binary validation in `ImageIngestionService`:

### 4.1 Magic Bytes Inspection
Before any image library processing, raw binary prefixes are verified:
- **JPEG**: `data.startswith(b"\xFF\xD8\xFF")`
- **PNG**: `data.startswith(b"\x89PNG\r\n\x1a\n")`
- **WebP**: `data.startswith(b"RIFF") and data[8:12] == b"WEBP"`

Files failing this binary signature check are rejected immediately with an HTTP 400 error.

### 4.2 Structural Validation & Decompression Bomb Prevention
- Upload size is capped at `15 MB` (configurable via `MAX_IMAGE_SIZE_MB`).
- Maximum pixel dimensions are constrained to `12,000 x 12,000 px` to prevent Pillow decompression memory exhaustion bombs.
- Minimum dimensions are enforced (`10 x 10 px`) to reject zero-information thumbnails.

### 4.3 Filename Sanitization & Directory Traversal Prevention
- User-provided filenames are completely stripped of directory traversal sequences (`..`, `/`, `\`) and null bytes (`\0`).
- Filenames are sanitized to alphanumeric tokens, hyphens, and underscores.
- The file extension is determined **strictly by detected image format**, ignoring any misleading client extension.

---

## 5. Cryptographic Evidence Chain

1. **Pre-Storage SHA-256 Digest**:
   Every package surface image is hashed before persistence:
   ```python
   sha256 = hashlib.sha256(content_bytes).hexdigest()
   ```
   This hash is stored in `inspection_surfaces.sha256_hash` and embedded into generated PDF dossiers.
2. **Deterministic Label Fingerprints**:
   Canonical declarations are hashed using SHA-256. Any subtle modification (e.g. altering `250 g` to `220 g`) completely changes the fingerprint, alerting the system to packaging alterations.
3. **Non-Overwriting Observation Progression**:
   When an observation is revised, the original record retains `is_latest: false` and points to its replacement. The full historical chain of evidence remains queryable for courtroom scrutiny.

---

## 6. Audit Trail & Non-Repudiation

Every administrative and enforcement action is recorded in the `audit_logs` table:
- `user_id`: UUID of the authenticated actor.
- `action`: Specific operation (e.g. `OBSERVATION_REVISED`, `RULE_EVALUATION_OVERRIDDEN`, `REPORT_GENERATED`).
- `entity_type` & `entity_id`: Target resource.
- `previous_state` & `new_state`: JSON diff capturing exact modifications.
- `ip_address` & `user_agent`: Network origin metadata.
- `created_at`: UTC timestamp.

The database grants no `UPDATE` or `DELETE` permissions on `audit_logs` in production environments.
