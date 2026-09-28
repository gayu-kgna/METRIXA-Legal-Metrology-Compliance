# METRIXA (मेट्रिक्सा)

> **Next-Generation Legal Metrology Packaging Inspection & Enforcement Platform**  
> *Developed for the Smart India Hackathon (SIH) 2026*  
> **Statutory Framework**: *The Legal Metrology Act, 2009 & Legal Metrology (Packaged Commodities) Rules, 2011 (as amended)*

---

## 1. Executive Summary & Problem Statement

Pre-packaged commodities sold across Indian retail markets and e-commerce ecosystems frequently violate statutory labeling mandates under the **Legal Metrology (Packaged Commodities) Rules, 2011 (PCMR 2011)**. Key systemic challenges faced by enforcement officers include:
1. **Omission of Mandatory Declarations**: Missing Maximum Retail Price (MRP), net quantity, manufacturer/packer identity, manufacturing dates, or consumer grievance redressal coordinates.
2. **Deceptive Packaging & Shrinkflation**: Subtle reductions in net quantity while maintaining price and outer packaging dimensions, evading consumer notice.
3. **Dual Pricing & Sticker Overprinting**: Unauthorized stickers or conflicting retail prices printed on packaging surfaces.
4. **Non-Standard Measuring Units**: Illegal imperial or non-metric units contrary to Rule 12.
5. **Lack of Cryptographic Evidence & Non-Repudiation**: Field inspection reports contested in court due to unverified photo tampering, missing audit trails, or fabricated measurements.

**Metrixa solves this problem through an end-to-end, trustworthy, deterministic regulatory enforcement platform.**

---

## 2. Core Architectural Pillars

Metrixa is engineered around four uncompromising architectural guarantees:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        METRIXA ARCHITECTURE                            │
├────────────────────────────────────────────────────────────────────────┤
│  [Perception Layer]                                                   │
│    Intelligent Camera HUD (Tactile Guard) & File Upload                │
│    CV Preprocessing (Bilateral Filter, CLAHE, Deskew, Glare/Blur Alert) │
│    Multi-Engine OCR (PaddleOCR, Tesseract, EasyOCR fallback)           │
│                           │                                            │
│                           ▼ (Evidence Objects)                         │
│  [Deterministic Boundary] (STRICT SEPARATION)                         │
│    AI / OCR suggests observations; AI NEVER renders legal verdicts     │
│                           │                                            │
│                           ▼                                            │
│  [Rule & Metrology Engine]                                             │
│    Authoritative Rule Definitions (G.S.R. 202(E) dated 7th March 2011) │
│    Units Normalizer (Rule 12 Standard Metric Units)                    │
│    Calibrated PDP Geometry (Rule 7 Font Height & Area Calibration)      │
│    Verdicts: PASS / FAIL / REVIEW / INDETERMINATE / NOT_APPLICABLE      │
│                           │                                            │
│                           ▼                                            │
│  [Immutable Ledger & Cryptographic Chain]                              │
│    SHA-256 Hashes of original image bytes                              │
│    Product Ledger & Label Version Diffing (Detects Shrinkflation)      │
│    Immutable Append-Only Audit Logs & Cryptographic PDF Dossier        │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Strict Separation Between Perception and Legal Adjudication**:
   - Neural models and OCR suggest text candidates with confidence scores.
   - **Deterministic Python rule evaluators alone make legal decisions.** No black-box LLM or probabilistic AI is permitted to decide statutory compliance.
2. **Camera Workflow Guard**:
   - Web camera hardware (`getUserMedia`) is **NEVER automatically activated** on page load, route change, or tab navigation.
   - Explicit user click on `[Camera HUD]` or `[Upload Photo]` is required, preventing unconsented stream capture.
3. **Cryptographic Evidence Integrity**:
   - Every uploaded package surface is fingerprinted with an immutable **SHA-256 digest** on its exact original bytes.
   - Observations are versioned (`revision: 1, 2, ...`), and prior observations are marked `is_latest: false` rather than deleted.
4. **Persistent Product Ledger & Historical Timeline**:
   - Package labels are tracked across time and geographical inspections via **GTIN/Barcode**.
   - Cryptographic label fingerprints (`SHA-256`) enable deterministic change detection across packaging revisions, exposing **shrinkflation** and clandestine price inflation.

---

## 3. Platform Capabilities

- **Six-Surface Spatial Inspection Workspace**: Full packaging geometry coverage (`FRONT_PDP`, `BACK`, `LEFT`, `RIGHT`, `TOP`, `BOTTOM`).
- **Principal Display Panel (PDP) Calibration**: Authentic millimeter font height and quadrant verification under Rule 7 and Rule 12.
- **Intelligent Camera HUD**: Real-time bounding-box guidance, contrast/glare/motion-blur alerts, and one-tap fallback to file upload.
- **Human Adjudication Workflow**: Side-by-side evidence inspection, visual character confusion resolution (`Rs. 4S0` vs `Rs. 450`), and dual-pricing conflict resolution.
- **Legal Metrology PDF Dossier**: Court-ready explainable reports with embedded evidence snapshots, statutory citations, and verification timestamps.
- **Factual Analytics Dashboard**: Real-time KPI metrics, compliance distribution, geographic defect hotspots, and product timeline evolution.

---

## 4. Benchmark Performance & Golden Dataset

Metrixa includes a curated **15-case synthetic Golden Dataset** testing edge cases under strict non-production conditions:

| Metric | Verification Result |
| :--- | :--- |
| **Total Test Cases** | 15 synthetic cases |
| **Benchmark Accuracy** | **100.0% (15/15 passed)** |
| **Field Match Rate** | 110/110 fields verified |
| **Normalization Accuracy** | 15/15 standard metric transformations |
| **Benchmark Execution Time** | ~0.015 seconds |
| **Backend Test Suite** | **74/74 passed (`pytest`)** |
| **Frontend Test Suite** | **53/53 passed (`vitest`)** |
| **Production Build** | **Succeeded cleanly (`tsc -b && vite build`)** |

---

## 5. Technology Stack

- **Backend**: FastAPI (Python 3.14), SQLAlchemy 2.0 (Async), PostgreSQL (Docker), Pydantic v2, PyPDF, Pillow.
- **Frontend**: React 18, TypeScript, Vite, TailwindCSS / Lucide Icons.
- **Security**: JWT (HS256), Argon2 / bcrypt password hashing, Magic Byte verification (JPEG, PNG, WebP), Append-only audit logs.

---

## 6. Quick Start

### Prerequisites
- Python 3.10+ (Tested on Python 3.14.2)
- Node.js 18+ (Tested on Node.js 20+)
- Docker & Docker Compose (for PostgreSQL)

```bash
# 1. Start Database
docker-compose up -d

# 2. Run Backend
cd backend
python -m venv ../.venv
../.venv/Scripts/activate      # On Windows
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_phase10_demo.py
uvicorn app.main:app --port 8080 --reload

# 3. Run Frontend
cd ../frontend
npm install
npm run dev
```

Visit `http://localhost:5173` to explore the Metrixa dashboard.
For complete setup instructions, consult [SETUP.md](file:///c:/Users/kkavi/My%20Projects/Metrixa/SETUP.md).
For a guided 3–5 minute judge walk-through, see [DEMO_GUIDE.md](file:///c:/Users/kkavi/My%20Projects/Metrixa/DEMO_GUIDE.md).

---

## 7. Production Deployment Guide (Railway, Supabase, Vercel, GitHub)

Metrixa is engineered for a secure, zero-hardcoding cloud deployment architecture:

```
┌───────────────────────────┐      ┌───────────────────────────┐
│     Vercel (Frontend)     │      │     Railway (Backend)     │
│  - React 19 + Vite SPA    │ HTTP │  - Python 3.11 Container  │
│  - Static Asset CDN       ├─────►│  - FastAPI + Uvicorn      │
│  - SPA Rewrites           │ REST │  - Tesseract OCR + OSD    │
│  - VITE_API_BASE_URL      │      │  - OpenCV Libs            │
└───────────────────────────┘      └─────────────┬─────────────┘
                                                 │
                                                 ▼
                                   ┌───────────────────────────┐
                                   │    Supabase (Database)    │
                                   │  - Managed PostgreSQL 16  │
                                   │  - Session/Txn Pooler     │
                                   │  - SSL Required           │
                                   └───────────────────────────┘
```

### 1. Database Provisioning (Supabase)
1. Create a new PostgreSQL project on [Supabase](https://supabase.com).
2. Under **Project Settings > Database > Connection string**, copy the URI.
   - For direct connection (port `5432`):
     `postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`
   - For transaction pooler (port `6543`, recommended for high concurrency):
     `postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres`
3. *Note*: Metrixa automatically normalizes `postgres://` and `postgresql://` URIs and adjusts `sslmode=require` to `ssl=require` for asyncpg.

### 2. Backend Container Deployment (Railway)
1. In [Railway](https://railway.app), create a new project and select **Deploy from GitHub repo**.
2. Set the **Root Directory** to `/backend`. Railway will automatically detect `backend/Dockerfile`.
3. Under **Settings > Networking**:
   - Railway injects the `$PORT` environment variable dynamically. The container binds to `0.0.0.0:$PORT` automatically.
   - Healthcheck Path: `/health` (or `/api/v1/health`).
4. Under **Volumes**:
   - Add a persistent volume mounted at `/app/storage` (size: 5–10 GB) to ensure original surface images, OCR caches, and generated PDF inspection dossiers persist across deploys.
5. Under **Variables**, configure the required environment variables:

| Variable | Recommended Production Value | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Enables production security guards |
| `DEBUG` | `false` | Disables debug mode |
| `PORT` | *(Provided by Railway)* | Server binding port |
| `HOST` | `0.0.0.0` | Container network interface |
| `DATABASE_URL` | `postgresql://postgres:...` | Supabase PostgreSQL connection string |
| `JWT_SECRET_KEY` | *(High entropy 32+ chars)* | Sign token (e.g. `openssl rand -hex 32`) |
| `STORAGE_ROOT` | `/app/storage` | Persistent volume mount path |
| `STORAGE_BACKEND` | `local` | Filesystem/volume storage backend |
| `CORS_ORIGINS` | `https://your-frontend.vercel.app` | Allowed frontend origins (comma-separated, NO `*`) |

6. **Database Migration Execution**:
   - Set Railway **Pre-deploy Command** (or run via Railway CLI):
     ```bash
     alembic upgrade head
     ```
   - Optional initial administrative seed:
     ```bash
     python scripts/seed_phase10_demo.py
     ```

### 3. Frontend Deployment (Vercel)
1. In [Vercel](https://vercel.com), import your GitHub repository.
2. Configure project settings:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. Under **Environment Variables**, add:

| Variable | Production Value | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `https://<your-railway-app>.up.railway.app/api/v1` | URL of the Railway backend API |

4. Vercel automatically deploys with HTTPS enabled, satisfying the browser security context (`window.isSecureContext`) required for the **Camera HUD** (`navigator.mediaDevices.getUserMedia`).
5. Direct navigation to client-side routes (e.g. `/inspections`, `/dashboard`, `/adjudication`) is handled seamlessly via `frontend/vercel.json` SPA rewrite rules.

---

## 8. Verification & Operational Health Check

- **API Liveness Probe**: `GET /health` (Returns HTTP 200 `{"status": "healthy"}`)
- **Readiness & DB Probe**: `GET /api/v1/health` (Verifies live PostgreSQL connectivity)
- **Interactive Documentation**: `GET /api/v1/docs` (Swagger UI)

