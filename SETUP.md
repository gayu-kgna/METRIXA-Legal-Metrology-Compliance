# Metrixa Deployment & Environment Setup Guide

This guide details the complete procedure to install, configure, verify, and run the Metrixa Legal Metrology Enforcement Platform in both local development and production environments.

---

## 1. System Requirements

### Hardware Requirements
- **CPU**: Dual-core x86_64 or ARM64 processor (Quad-core recommended for OCR pipelines).
- **RAM**: Minimum 4 GB (8 GB recommended for simultaneous CV and local OCR engines).
- **Disk**: 2 GB free disk space.

### Software Prerequisites
- **Operating System**: Windows 10/11, Ubuntu 22.04 LTS+, or macOS.
- **Python**: Version 3.10 to 3.14 (Validated on Python 3.14.2).
- **Node.js**: Version 18.0 or higher (Validated on Node 20+).
- **Docker**: Docker Engine 24+ and Docker Compose v2 (for PostgreSQL).

---

## 2. Infrastructure Setup (Database)

Metrixa requires PostgreSQL 15+ with standard UUID extensions.

```bash
# From repository root:
docker-compose up -d
```

Verify that the database container is operational:
```bash
docker ps --filter "name=metrixa-postgres"
```

Connection parameters configured in `docker-compose.yml`:
- **Host**: `localhost`
- **Port**: `5432`
- **Database**: `metrixa_db`
- **User**: `metrixa`
- **Password**: `metrixa_secret_dev_2026`

---

## 3. Backend Setup

### 3.1 Virtual Environment Installation
```bash
# Navigate to backend directory
cd backend

# Create virtual environment in root
python -m venv ../.venv

# Activate virtual environment
# Windows (PowerShell):
..\.venv\Scripts\Activate.ps1
# Windows (CMD):
..\.venv\Scripts\activate.bat
# Linux / macOS:
source ../.venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.2 Environment Configuration
Copy the configuration template:
```bash
cp .env.example .env
```

Key environment variables:
| Variable | Description | Development Default | Production Requirement |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | Runtime mode | `development` | Must be `production` |
| `DEBUG` | Verbose debug logging | `true` | Must be `false` |
| `DATABASE_URL` | PostgreSQL asyncpg URI | Local container URI | Production managed DB URI |
| `JWT_SECRET_KEY` | HMAC token secret | Dev secret placeholder | High-entropy string (>= 32 chars) |
| `MAX_IMAGE_SIZE_MB`| File upload limit | `15` | Configurable |

> [!IMPORTANT]
> When `ENVIRONMENT=production`, Metrixa executes an automated startup validation that immediately halts execution if default dev secrets or active debug modes are detected.

### 3.3 Database Migrations
Apply Alembic database migrations to bring the schema to head:
```bash
alembic upgrade head
```

### 3.4 Demo Data Seeding
Populate realistic demonstration cases (Flagship Green Tea shrinkflation evolution, dual pricing conflict, and missing origin defect):
```bash
python scripts/seed_phase10_demo.py
```

### 3.5 Launching the Backend Server
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```
The API Swagger documentation will be accessible at: `http://127.0.0.1:8080/api/v1/docs`

---

## 4. Frontend Setup

### 4.1 Dependency Installation
```bash
# In a separate terminal, navigate to frontend directory
cd frontend

# Install npm dependencies
npm install
```

### 4.2 Starting Development Server
```bash
npm run dev
```
The client interface will launch at: `http://localhost:5173` (or `http://localhost:3000`).

### 4.3 Building for Production
Validate production bundle generation:
```bash
npm run build
```
The compiled, type-checked artifacts will be created in `frontend/dist/`.

---

## 5. Verification & Testing

### 5.1 Execute Backend Test Suite
```bash
cd backend
..\.venv\Scripts\pytest
```
*Expected: 74/74 tests passed.*

### 5.2 Execute Frontend Test Suite
```bash
cd frontend
npm test -- --run
```
*Expected: 53/53 tests passed.*

### 5.3 Execute Golden Dataset Benchmark
```bash
cd backend
..\.venv\Scripts\python scripts/run_golden_benchmark.py
```
*Expected: 15/15 cases passed (100.0% accuracy).*

### 5.4 Execute Live 20-Gate Comprehensive Verification
```bash
cd backend
..\.venv\Scripts\python scripts/verify_phase10_live.py
```
*Expected: 20/20 gates passed.*

---

## 6. Safe Reset Procedure

To return the demonstration environment to a pristine state before presentation:
```bash
cd backend
..\.venv\Scripts\python scripts/reset_demo_data.py
```
This safely clears inspection artifacts and re-seeds all demonstration scenarios.
