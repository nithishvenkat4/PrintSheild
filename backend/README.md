# PrintShield — Phase 1 Backend

Privacy-preserving local printing platform backend implementing the frozen Phase 1 Engineering Specification.

> **Core Principle:** "Don't give the shop your document. Give them temporary permission to print it."

---

## 1. Architecture Overview

PrintShield replaces insecure document sharing (WhatsApp, Bluetooth, USB, email) at local printing shops with a controlled, temporary print job lifecycle:

```text
Customer                          Backend / S3                           Shop
   │                                   │                                  │
   ├────── 1. Request Upload URL ─────►│                                  │
   │◄───── 2. Presigned S3 URL ────────┤                                  │
   ├────── 3. Upload File directly ───►│ (S3 Private Bucket)              │
   ├────── 4. Complete Upload ────────►│                                  │
   ├────── 5. Create Job (Shop, Copies)►│                                  │
   │                                   ├────── 6. Appears in Queue ──────►│
   │                                   │◄───── 7. Start Job (Atomic) ─────┤
   │                                   │◄───── 8. Get Download URL ───────┤
   │                                   │────── 9. Render & Print ─────────┤
   │                                   │◄───── 10. Complete / Fail ───────┤
   │                                   ├────── 11. Delete from S3 ────────┤
   ▼                                   ▼                                  ▼
```

### Key Highlights
- **Direct S3 Presigned Uploads & Downloads**: Documents never pass through application memory. Presigned upload URLs expire in 5 minutes; download URLs expire in 120 seconds.
- **Atomic State Transitions**: Concurrency-safe job state machine (`WAITING` -> `PRINTING` -> `COMPLETED`/`FAILED`/`CANCELLED`/`EXPIRED`).
- **Cryptographic Access Control**: JWT Bearer tokens with strict role separation (`CUSTOMER`, `SHOP_OWNER`, `ADMIN`).
- **PostGIS Geographic Queries**: Shop discovery via spatial queries with Haversine fallback for SQLite development/tests.
- **Audit Logging**: Comprehensive non-repudiation audit trails for all sensitive actions.
- **Automated Lifecycle Cleanup**: Background cleanup worker deleting S3 objects and marking records on job completion, cancellation, or expiry.

---

## 2. Technology Stack

- **Framework**: FastAPI (Python 3.12 / 3.13)
- **Database ORM**: SQLAlchemy 2.0 (Declarative Mapped columns)
- **Spatial Extension**: PostGIS via GeoAlchemy2 & Shapely
- **Database Migrations**: Alembic
- **Authentication**: PyJWT + bcrypt
- **Cloud Storage**: AWS S3 via boto3 (with automatic mock fallback for offline tests)
- **Validation**: Pydantic v2
- **Testing**: pytest, pytest-asyncio, httpx

---

## 3. Directory Layout

```text
backend/
├── alembic/                      # Database migrations
│   ├── versions/
│   │   └── 001_initial_phase1_schema.py
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── api/v1/                   # API route handlers
│   │   ├── auth.py               # /api/v1/auth (register, login, me)
│   │   ├── shops.py              # /api/v1/shops (create, me, qr, nearby)
│   │   ├── documents.py          # /api/v1/documents (upload-url, complete)
│   │   └── jobs.py               # /api/v1/jobs & /api/v1/shop/jobs
│   ├── core/                     # Application configurations & security
│   │   ├── config.py             # Pydantic settings & env loading
│   │   ├── dependencies.py       # Auth guards & role dependencies
│   │   ├── exceptions.py         # Standardized error codes & handlers
│   │   ├── rate_limit.py         # Sliding window rate limiter
│   │   └── security.py           # Bcrypt & JWT token management
│   ├── db/                       # Database session & types
│   │   ├── base.py               # UTCDatetime, PointGeography, Base
│   │   └── session.py            # Engine & sessionmaker
│   ├── models/                   # SQLAlchemy database models
│   │   ├── user.py               # User & UserRole
│   │   ├── shop.py               # Shop & geospatial location
│   │   ├── document.py           # Document metadata
│   │   ├── print_job.py          # PrintJob & PrintJobStatus state machine
│   │   └── audit_log.py          # AuditLog & AuditAction
│   ├── schemas/                  # Pydantic request & response schemas
│   │   ├── auth.py
│   │   ├── shop.py
│   │   ├── document.py
│   │   └── job.py
│   ├── services/                 # Business logic layer
│   │   ├── auth_service.py
│   │   ├── shop_service.py
│   │   ├── document_service.py
│   │   ├── job_service.py
│   │   ├── s3_service.py
│   │   └── audit_service.py
│   ├── workers/                  # Background jobs
│   │   └── cleanup.py            # Expired job & document cleanup
│   └── main.py                   # FastAPI entrypoint & middleware
├── tests/                        # Comprehensive test suite (100% passing)
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_shops.py
│   ├── test_documents.py
│   ├── test_jobs.py
│   ├── test_shop_queue.py
│   ├── test_concurrency.py
│   ├── test_cleanup.py
│   └── test_e2e_golden_path.py
├── docker-compose.yml            # PostgreSQL 16 + PostGIS 3.4
├── requirements.txt
├── .env.example
└── README.md
```

---

## 4. Setup and Installation

### 1. Prerequisites
- Python 3.12+ (or Python 3.13)
- Docker & Docker Compose (for PostgreSQL/PostGIS)

### 2. Environment Configuration
```bash
cp .env.example .env
```

### 3. Start Database (PostgreSQL + PostGIS)
```bash
docker compose up -d
```

### 4. Install Dependencies
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 5. Run Database Migrations
```bash
alembic upgrade head
```

### 6. Start the Development Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
API Documentation will be live at `http://localhost:8000/docs`.

---

## 5. Running the Test Suite

Tests use an isolated SQLite in-memory database with mock S3 storage, requiring zero external services:

```bash
pytest -v tests
```

To run a specific test suite:
```bash
pytest -v tests/test_e2e_golden_path.py
pytest -v tests/test_concurrency.py
```

---

## 6. API Catalog

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Public | Register new customer or shop owner |
| `POST` | `/api/v1/auth/login` | Public | Authenticate and obtain JWT token |
| `GET` | `/api/v1/auth/me` | Authenticated | Get current authenticated user |
| `POST` | `/api/v1/shops` | Shop Owner | Register a new shop location |
| `GET` | `/api/v1/shops/me` | Shop Owner | Get own shop details |
| `PATCH` | `/api/v1/shops/me` | Shop Owner | Update shop details or status |
| `GET` | `/api/v1/shops/qr/{qr_token}` | Public | Resolve shop details by QR code |
| `GET` | `/api/v1/shops/nearby` | Public | Find shops within radius (geospatial) |
| `POST` | `/api/v1/documents/upload-url` | Customer | Request presigned S3 upload URL |
| `POST` | `/api/v1/documents/{id}/complete` | Customer | Verify and complete document upload |
| `POST` | `/api/v1/jobs` | Customer | Create print job with copies and shop |
| `GET` | `/api/v1/jobs` | Customer | List customer's print jobs |
| `GET` | `/api/v1/jobs/{id}` | Customer / Shop | Get print job detail |
| `POST` | `/api/v1/jobs/{id}/cancel` | Customer | Cancel print job (WAITING only) |
| `GET` | `/api/v1/shop/jobs` | Shop Owner | View FIFO print queue |
| `POST` | `/api/v1/shop/jobs/{id}/start` | Shop Owner | Transition job to PRINTING |
| `POST` | `/api/v1/shop/jobs/{id}/document-access` | Shop Owner | Get 120s presigned download URL |
| `POST` | `/api/v1/shop/jobs/{id}/complete` | Shop Owner | Complete print job and delete file |
| `POST` | `/api/v1/shop/jobs/{id}/fail` | Shop Owner | Mark job failed (retains for retry) |
| `GET` | `/health` | Public | Service health check |
