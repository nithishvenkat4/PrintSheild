# PrintShield — Phase 1 Engineering Specification
## Frozen API Contract + Database Schema + Integration Contract
### Version 1.0 — Single Source of Truth

> **Project principle:** “Don’t give the shop your document. Give them temporary permission to print it.”
>
> This specification defines the Phase 1 contract for the PrintShield backend, web application, Android application, database, storage, security, print-job lifecycle, and team integration.

---

# 1. Project Identity

**Project Name:** PrintShield

**Phase:** Phase 1

**Primary Goal:** Build a privacy-preserving local printing platform that allows customers to submit documents to a registered printing shop through temporary print jobs rather than reusable document sharing.

---

# 2. Core Problem

At local printing/Xerox shops, users commonly send sensitive documents such as Aadhaar, PAN, certificates, medical reports, and bank documents through WhatsApp, email, Bluetooth, USB drives, or other reusable channels.

This creates several problems:

- The shop receives a reusable digital copy.
- The customer has little visibility into document handling.
- Files may remain on computers or phones after printing.
- Documents can be forwarded or reused.
- Customers have no clear job-level lifecycle.
- Crowded shops make manual coordination difficult.

---

# 3. Core Solution

PrintShield creates a temporary controlled print job.

The customer:

1. Selects a printing shop.
2. Uploads a document.
3. Selects the number of copies.
4. Creates a print job.
5. The shop sees the job in its queue.
6. The shop temporarily accesses the document.
7. The document is printed.
8. The job is completed.
9. Access is revoked and temporary document storage is cleaned up.

---

# 4. Security Positioning

PrintShield should claim:

- reduced document exposure
- temporary access
- controlled print jobs
- expiry
- deletion/cleanup
- audit logging
- shop-level authorization
- customer-level authorization
- private cloud storage

PrintShield must **not** claim that a shop can physically never copy a document after rendering it.

The correct security statement is:

> PrintShield minimizes unnecessary document exposure, retention, and unauthorized reuse through temporary access, controlled jobs, expiry, deletion, and auditability.

---

# 5. Primary Customer Flow

The primary real-world flow is:

```text
Scan → Upload → Copies → Send → Collect
```

Shop QR is a core entry point.

---

# 6. Shop QR Requirement

Every registered shop receives a unique QR token.

The QR identifies the shop only.

It does not contain:

- customer identity
- document identity
- document contents
- password
- JWT
- private storage URL

Example QR target:

```text
https://printshield.app/shop/<qr_token>
```

The web application can resolve this token through the public shop-resolution API.

---

# 7. Alternative Customer Entry Points

PrintShield supports three practical entry methods:

### Primary

Shop QR.

### Secondary

Android Share → PrintShield.

### Secondary

Standalone app → choose shop.

The QR flow is the primary real-world flow because it is fast and feasible in crowded printing shops.

---

# 8. Android Share Flow

A customer can share a PDF/image from another application:

```text
WhatsApp / Files / Gallery
        ↓
Share
        ↓
PrintShield
        ↓
Choose Shop
        ↓
Copies
        ↓
Create Job
```

No WhatsApp API integration is required.

PrintShield receives the shared file through Android's standard Sharesheet/Intent mechanism.

---

# 9. Nearby Shop Discovery

When a shop registers, its default location is stored.

Customers can request nearby shops using their current foreground location.

PrintShield does not continuously track customer location.

Location is requested only when the customer chooses the nearby-shop feature.

If location permission is denied, the customer can still use QR scanning.

---

# 10. Location Storage Model

Shop location is stored as:

```text
GEOGRAPHY(Point, 4326)
```

PostGIS is used for spatial queries.

Customer location is not stored in a dedicated Phase 1 table.

---

# 11. Nearby-Shop Query

The backend uses:

```sql
ST_DWithin
```

to filter shops within the requested radius.

Results are sorted by distance.

Recommended range:

```text
100 m → 10,000 m
```

Recommended default:

```text
5 km
```

---

# 12. Nearby-Shop Endpoint

```http
GET /api/v1/shops/nearby
```

Query parameters:

```text
latitude
longitude
radius
limit
```

Example:

```http
GET /api/v1/shops/nearby?latitude=11.0168&longitude=76.9558&radius=5000&limit=20
```

---

# 13. Nearby-Shop Parameter Constraints

```text
latitude: -90 to 90
longitude: -180 to 180
radius: 100 to 10000 meters
limit: 1 to 50
```

Invalid values return validation errors.

---

# 14. Nearby-Shop Response

```json
{
  "data": {
    "shops": [
      {
        "id": "uuid",
        "name": "Sri Lakshmi Xerox",
        "address": "Main Road",
        "distance_meters": 350,
        "is_open": true
      }
    ]
  }
}
```

---

# 15. Shop Registration Location

Shop creation requires:

```json
{
  "name": "Sri Lakshmi Xerox",
  "phone": "+919876543210",
  "address": "123 Main Road, Coimbatore",
  "latitude": 11.0168,
  "longitude": 76.9558
}
```

The backend converts latitude/longitude into the PostGIS location field.

---

# 16. Roles

PrintShield has three roles:

```text
CUSTOMER
SHOP_OWNER
ADMIN
```

---

# 17. Customer Responsibilities

A customer can:

- register
- log in
- manage their account
- discover nearby shops
- resolve shop QR codes
- upload documents
- create print jobs
- view their own jobs
- cancel eligible jobs
- view job history

A customer cannot:

- access another customer's jobs
- access another customer's documents
- access a shop's queue
- start or complete a shop job

---

# 18. Shop Owner Responsibilities

A shop owner can:

- manage their shop
- update shop information
- see their QR
- view their own queue
- start jobs belonging to their shop
- temporarily access eligible documents
- complete jobs
- fail jobs
- retry failed jobs

A shop owner cannot:

- access another shop's jobs
- access another shop's documents
- access arbitrary customer documents

---

# 19. Admin Responsibilities

An admin can:

- view users
- view shops
- view jobs
- manage platform-level information
- inspect audit logs
- perform administrative operations

Admin privileges must still be implemented explicitly rather than inferred from UI behavior.

---

# 20. Authentication

PrintShield uses JWT Bearer authentication.

Header:

```http
Authorization: Bearer <JWT>
```

JWT should contain only the information necessary for authentication/authorization, such as:

```text
user_id
role
expiration
```

It must not contain:

- document contents
- document storage URLs
- sensitive customer information

---

# 21. Password Storage

Passwords must never be stored as plaintext.

The database stores:

```text
password_hash
```

using a secure password-hashing mechanism.

---

# 22. Auth Register Endpoint

```http
POST /api/v1/auth/register
```

Request:

```json
{
  "name": "Nithish",
  "email": "nithish@example.com",
  "password": "StrongPassword123"
}
```

---

# 23. Auth Register Response

HTTP:

```text
201 CREATED
```

Response:

```json
{
  "data": {
    "user": {
      "id": "uuid",
      "name": "Nithish",
      "email": "nithish@example.com",
      "role": "CUSTOMER"
    }
  }
}
```

---

# 24. Auth Login Endpoint

```http
POST /api/v1/auth/login
```

Request:

```json
{
  "email": "nithish@example.com",
  "password": "StrongPassword123"
}
```

---

# 25. Auth Login Response

```json
{
  "data": {
    "access_token": "jwt-token",
    "token_type": "bearer",
    "user": {
      "id": "uuid",
      "name": "Nithish",
      "email": "nithish@example.com",
      "role": "CUSTOMER"
    }
  }
}
```

HTTP:

```text
200 OK
```

---

# 26. Current User Endpoint

```http
GET /api/v1/auth/me
```

Response:

```json
{
  "data": {
    "id": "uuid",
    "name": "Nithish",
    "email": "nithish@example.com",
    "role": "CUSTOMER"
  }
}
```

HTTP:

```text
200 OK
```

---

# 27. Shop Create Endpoint

```http
POST /api/v1/shops
```

Authorization:

```text
SHOP_OWNER
ADMIN
```

Request:

```json
{
  "name": "Sri Lakshmi Xerox",
  "phone": "+919876543210",
  "address": "123 Main Road, Coimbatore",
  "latitude": 11.0168,
  "longitude": 76.9558
}
```

---

# 28. Shop Table

```text
shops
```

Fields:

```text
id                  UUID PRIMARY KEY
owner_id            UUID NOT NULL REFERENCES users(id)
name                VARCHAR(150) NOT NULL
phone               VARCHAR(20) NOT NULL
address             TEXT NOT NULL
location            GEOGRAPHY(Point, 4326) NOT NULL
qr_token            UUID UNIQUE NOT NULL
is_open             BOOLEAN NOT NULL DEFAULT TRUE
is_verified         BOOLEAN NOT NULL DEFAULT FALSE
created_at          TIMESTAMPTZ NOT NULL
updated_at          TIMESTAMPTZ NOT NULL
```

Phase 1 assumption:

```text
One shop owner owns one shop.
```

---

# 29. Get Own Shop

```http
GET /api/v1/shops/me
```

Authorization:

```text
SHOP_OWNER
ADMIN
```

Returns the authenticated owner's shop.

---

# 30. Update Own Shop

```http
PATCH /api/v1/shops/me
```

Allowed fields include:

```text
name
phone
address
is_open
latitude
longitude
```

The backend must validate location ranges before updating PostGIS.

---

# 31. Public QR Resolution

```http
GET /api/v1/shops/qr/{qr_token}
```

This endpoint is public.

Response:

```json
{
  "data": {
    "shop_id": "uuid",
    "name": "Sri Lakshmi Xerox",
    "address": "Main Road",
    "is_open": true
  }
}
```

Only safe shop information is exposed.

---

# 32. Shop QR Security

The QR endpoint must never expose:

- owner information
- customer information
- private document information
- JWTs
- S3 credentials
- internal database information

---

# 33. User Table

```text
users
```

Fields:

```text
id                  UUID PRIMARY KEY
name                VARCHAR(100) NOT NULL
email               VARCHAR(255) UNIQUE NOT NULL
password_hash       TEXT NOT NULL
role                user_role NOT NULL
is_active           BOOLEAN NOT NULL DEFAULT TRUE
created_at          TIMESTAMPTZ NOT NULL
updated_at          TIMESTAMPTZ NOT NULL
```

---

# 34. User Role Enum

```text
user_role:
CUSTOMER
SHOP_OWNER
ADMIN
```

---

# 35. Print Job as Core Business Object

The print job is the central business object.

Conceptually:

```text
Document
   ↓
Print Job
   ├── Customer
   ├── Shop
   ├── Copies
   ├── Status
   ├── Pickup Code
   ├── Expiry
   └── Permissions
```

---

# 36. Print Job Queue

The shop dashboard displays jobs in FIFO order.

Example:

```text
#101  2 copies
#102  1 copy
#103  5 copies
```

Multiple customers can submit jobs simultaneously.

---

# 37. Print Job Table

```text
print_jobs
```

Fields:

```text
id                  UUID PRIMARY KEY
customer_id         UUID NOT NULL REFERENCES users(id)
shop_id             UUID NOT NULL REFERENCES shops(id)
document_id         UUID UNIQUE NOT NULL
copy_count          SMALLINT NOT NULL
status              print_job_status NOT NULL
pickup_code         VARCHAR(6) NOT NULL
created_at          TIMESTAMPTZ NOT NULL
started_at          TIMESTAMPTZ NULL
completed_at        TIMESTAMPTZ NULL
expires_at          TIMESTAMPTZ NOT NULL
failure_reason      TEXT NULL
updated_at          TIMESTAMPTZ NOT NULL
```

---

# 38. Print Job Status Enum

```text
CREATED
WAITING
PRINTING
COMPLETED
CANCELLED
EXPIRED
FAILED
```

---

# 39. Print Job State Machine

```text
                 CREATED
                    │
                    ▼
                 WAITING
              ┌─────┼─────┐
              ▼     ▼     ▼
          PRINTING CANCELLED EXPIRED
          ┌────┴─────┐
          ▼          ▼
      COMPLETED     FAILED
```

---

# 40. Valid State Transitions

```text
CREATED → WAITING
CREATED → CANCELLED

WAITING → PRINTING
WAITING → CANCELLED
WAITING → EXPIRED

PRINTING → COMPLETED
PRINTING → FAILED

FAILED → PRINTING
```

Terminal states:

```text
COMPLETED
CANCELLED
EXPIRED
```

---

# 41. Document Lifecycle

```text
UPLOADED → AVAILABLE → DELETE
```

A document is created as an upload object, verified, made available to the job, and deleted after the appropriate terminal lifecycle event.

---

# 42. Document Table

```text
documents
```

Fields:

```text
id                  UUID PRIMARY KEY
owner_id            UUID NOT NULL REFERENCES users(id)
job_id              UUID UNIQUE NOT NULL
original_filename   VARCHAR(255) NOT NULL
storage_key         TEXT UNIQUE NOT NULL
mime_type           VARCHAR(100) NOT NULL
file_size           BIGINT NOT NULL
checksum_sha256     CHAR(64) NOT NULL
created_at          TIMESTAMPTZ NOT NULL
expires_at          TIMESTAMPTZ NOT NULL
deleted_at          TIMESTAMPTZ NULL
```

Actual file content is stored in S3, not PostgreSQL.

---

# 43. Document Ownership

The `owner_id` must identify the customer who uploaded the document.

The backend must verify:

```text
document.owner_id == authenticated_user.id
```

before allowing that customer to create a job from the document.

---

# 44. S3 Storage Principle

AWS S3 is object storage.

PostgreSQL stores metadata.

S3 stores the actual document.

The S3 bucket must be private.

Frontends must never receive AWS credentials.

---

# 45. S3 Object Key

Recommended object key:

```text
jobs/{job_id}/{random_filename}
```

Do not use:

```text
customer_name/original_filename
email/original_filename
aadhaar_number/original_filename
```

The storage key must not expose unnecessary identity information.

---

# 46. Presigned Upload URL

The client requests an upload URL:

```http
POST /api/v1/documents/upload-url
```

Request:

```json
{
  "filename": "aadhaar.pdf",
  "mime_type": "application/pdf",
  "file_size": 183421
}
```

---

# 47. Upload URL Response

```json
{
  "data": {
    "document_id": "uuid",
    "upload_url": "presigned-url",
    "expires_in": 300
  }
}
```

Recommended upload URL lifetime:

```text
5 minutes
```

---

# 48. Direct S3 Upload

The frontend/mobile client uploads directly to the presigned S3 URL.

Flow:

```text
Client
  ↓
FastAPI
  ↓
Presigned S3 URL
  ↓
Client
  ↓
Private S3
```

The actual file does not need to pass through the FastAPI server.

---

# 49. Document Completion Endpoint

```http
POST /api/v1/documents/{document_id}/complete
```

Request:

```json
{}
```

The backend checks that the expected object exists and validates its metadata/content before marking the document available.

---

# 50. Document Completion Response

```json
{
  "data": {
    "document_id": "uuid",
    "status": "AVAILABLE",
    "filename": "aadhaar.pdf",
    "size": 183421
  }
}
```

---

# 51. Allowed File Types

Phase 1 allows:

```text
PDF
JPEG / JPG
PNG
```

Maximum file size:

```text
20 MB
```

Maximum copy count:

```text
20
```

---

# 52. File Validation

Do not trust only:

```text
file extension
Content-Type
```

Validate:

- extension
- declared MIME type
- file signature/content where applicable
- file size
- storage metadata

Reject arbitrary executable or unsupported file types.

---

# 53. Job Creation Endpoint

```http
POST /api/v1/jobs
```

Request:

```json
{
  "shop_id": "shop-uuid",
  "document_id": "document-uuid",
  "copy_count": 2
}
```

All three fields are mandatory.

---

# 54. Job Creation Validation

The backend checks:

1. authenticated user is a customer
2. document exists
3. document belongs to the customer
4. document is available
5. document has not expired
6. shop exists
7. shop is active
8. copy count is between 1 and 20

If valid:

```text
CREATED → WAITING
```

---

# 55. Job Creation Response

HTTP:

```text
201 CREATED
```

Response:

```json
{
  "data": {
    "id": "job-uuid",
    "shop": {
      "id": "shop-uuid",
      "name": "Sri Lakshmi Xerox"
    },
    "document": {
      "id": "document-uuid",
      "filename": "aadhaar.pdf"
    },
    "copy_count": 2,
    "status": "WAITING",
    "pickup_code": "4821",
    "created_at": "2026-10-05T09:30:00Z",
    "expires_at": "2026-10-05T10:30:00Z"
  }
}
```

---

# 56. Pickup Code

Each job receives a short pickup/identification code.

Example:

```text
4821
```

The code is used to help identify a customer's job at the shop.

It is **not** a full authorization mechanism and must not be treated as an OTP for sensitive document access.

---

# 57. Copy Count

Copy count is mandatory.

Constraints:

```text
minimum: 1
maximum: 20
```

The customer-facing UI should make this simple:

```text
Copies

[ − ]  2  [ + ]

Send to Print
```

---

# 58. Print Settings

Phase 1 intentionally keeps print configuration simple.

Mandatory:

```text
document
copy count
shop
```

Optional/omitted from MVP:

```text
color
paper size
orientation
other advanced printer settings
```

The goal is to avoid confusing ordinary customers.

---

# 59. Customer Job List

```http
GET /api/v1/jobs
```

The endpoint returns only jobs owned by the authenticated customer.

Optional query filters:

```text
status
limit
cursor
```

---

# 60. Customer Job Details

```http
GET /api/v1/jobs/{job_id}
```

Authorization:

- customer can access their own job
- shop owner can access a job belonging to their shop
- admin can access all

---

# 61. Cancel Job

```http
POST /api/v1/jobs/{job_id}/cancel
```

Customer-only operation.

Allowed state:

```text
WAITING
```

Transition:

```text
WAITING → CANCELLED
```

If the job is already:

```text
PRINTING
```

return:

```text
409 CONFLICT
```

---

# 62. Shop Queue Endpoint

```http
GET /api/v1/shop/jobs?status=WAITING&limit=20
```

The shop owner can see only jobs belonging to their own shop.

Queue ordering:

```text
created_at ASC
```

---

# 63. Shop Queue Response

```json
{
  "data": {
    "jobs": [
      {
        "id": "uuid",
        "pickup_code": "4821",
        "copy_count": 2,
        "filename": "aadhaar.pdf",
        "status": "WAITING",
        "created_at": "2026-10-05T09:30:00Z"
      }
    ]
  }
}
```

---

# 64. Start Job Endpoint

```http
POST /api/v1/shop/jobs/{job_id}/start
```

The backend checks:

- authenticated user owns the shop
- job belongs to that shop
- job status is WAITING
- job has not expired

Transition:

```text
WAITING → PRINTING
```

---

# 65. Atomic Job Start

Starting a job must be concurrency-safe.

Use a conditional database update such as:

```sql
UPDATE print_jobs
SET status = 'PRINTING',
    started_at = NOW(),
    updated_at = NOW()
WHERE id = :job_id
  AND status = 'WAITING';
```

Only one concurrent request should successfully transition the job.

This prevents two shop browser tabs from starting the same job simultaneously.

---

# 66. Document Access Endpoint

```http
POST /api/v1/shop/jobs/{job_id}/document-access
```

The backend checks:

- shop ownership
- job belongs to shop
- status is PRINTING
- job has not expired

Response:

```json
{
  "data": {
    "download_url": "presigned-url",
    "expires_in": 120
  }
}
```

---

# 67. Document Access Duration

Recommended shop download URL lifetime:

```text
120 seconds
```

The URL should be short-lived.

The shop application should request access only when the document is ready to be printed.

---

# 68. Complete Job Endpoint

```http
POST /api/v1/shop/jobs/{job_id}/complete
```

Transition:

```text
PRINTING → COMPLETED
```

The backend records:

```text
completed_at
updated_at
```

Document cleanup is initiated.

---

# 69. Fail Job Endpoint

```http
POST /api/v1/shop/jobs/{job_id}/fail
```

Request:

```json
{
  "reason": "Printer out of paper"
}
```

Transition:

```text
PRINTING → FAILED
```

The failure reason is stored in:

```text
failure_reason
```

---

# 70. Retry Failed Job

A failed job can transition:

```text
FAILED → PRINTING
```

The shop must still own the job.

The job must not have expired.

---

# 71. Background Expiry

A background cleanup process periodically checks:

```text
WAITING
CREATED
```

jobs where:

```text
expires_at < now
```

The job becomes:

```text
EXPIRED
```

and associated document cleanup is triggered.

---

# 72. Document Cleanup

Document cleanup should occur after appropriate terminal events:

```text
COMPLETED
CANCELLED
EXPIRED
```

The database records:

```text
deleted_at
```

and the S3 object is removed.

S3 lifecycle expiration should also be configured as a backup.

---

# 73. Logical Deletion Limitation

PrintShield can control and clean up its managed digital copy.

It cannot guarantee physical secure deletion from a shop-controlled computer after the file has been rendered or copied by that computer.

Therefore the project should describe cleanup as:

```text
logical deletion / removal / minimized retention
```

rather than claiming mathematically guaranteed physical destruction.

---

# 74. Audit Log Table

```text
audit_logs
```

Fields:

```text
id                  UUID PRIMARY KEY
actor_id            UUID NULL REFERENCES users(id)
job_id              UUID NULL REFERENCES print_jobs(id)
action              VARCHAR(50) NOT NULL
created_at          TIMESTAMPTZ NOT NULL
ip_address          INET NULL
metadata            JSONB NULL
```

---

# 75. Audit Actions

Supported actions include:

```text
USER_REGISTERED
USER_LOGIN
SHOP_CREATED
QR_ACCESSED
DOCUMENT_UPLOADED
JOB_CREATED
JOB_CANCELLED
JOB_STARTED
JOB_COMPLETED
JOB_FAILED
JOB_EXPIRED
DOCUMENT_DELETED
```

Do not log:

- document contents
- passwords
- JWTs
- unnecessary sensitive fields

---

# 76. Database Relationships

```text
users 1 ─── 0..1 shops

users 1 ─── N print_jobs

shops 1 ─── N print_jobs

print_jobs 1 ─── 1 documents

users 1 ─── N documents

print_jobs 1 ─── N audit_logs

users 1 ─── N audit_logs
```

---

# 77. Database Indexes

```sql
CREATE INDEX idx_print_jobs_customer
ON print_jobs(customer_id);

CREATE INDEX idx_print_jobs_shop_status
ON print_jobs(shop_id, status);

CREATE INDEX idx_print_jobs_expires
ON print_jobs(expires_at);

CREATE INDEX idx_documents_owner
ON documents(owner_id);

CREATE INDEX idx_audit_logs_job
ON audit_logs(job_id);

CREATE INDEX idx_shops_location
ON shops
USING GIST(location);
```

---

# 78. Complete Database Entity Set

Phase 1 contains:

```text
users
shops
documents
print_jobs
audit_logs
```

No separate customer-location table is required for Phase 1.

---

# 79. API Response Convention

Successful response:

```json
{
  "data": {}
}
```

Error response:

```json
{
  "error": {
    "code": "JOB_EXPIRED",
    "message": "This print job has expired."
  }
}
```

The API should maintain this structure consistently.

---

# 80. HTTP Status Codes

Use:

```text
200 OK
201 CREATED
204 NO CONTENT
400 BAD REQUEST
401 UNAUTHORIZED
403 FORBIDDEN
404 NOT FOUND
409 CONFLICT
413 PAYLOAD TOO LARGE
422 VALIDATION ERROR
429 TOO MANY REQUESTS
500 INTERNAL SERVER ERROR
```

---

# 81. Error Catalog

Authentication:

```text
AUTH_INVALID_CREDENTIALS
AUTH_TOKEN_EXPIRED
AUTH_TOKEN_INVALID
AUTH_INSUFFICIENT_ROLE
```

Shop:

```text
SHOP_NOT_FOUND
SHOP_INACTIVE
SHOP_NOT_OWNER
```

Document:

```text
DOCUMENT_NOT_FOUND
DOCUMENT_NOT_READY
DOCUMENT_EXPIRED
DOCUMENT_ACCESS_DENIED
DOCUMENT_INVALID_TYPE
DOCUMENT_TOO_LARGE
```

Job:

```text
JOB_NOT_FOUND
JOB_ACCESS_DENIED
JOB_INVALID_STATE
JOB_EXPIRED
JOB_ALREADY_PRINTING
JOB_CANNOT_CANCEL
INVALID_COPY_COUNT
```

Location:

```text
INVALID_LOCATION
```

QR:

```text
INVALID_QR
QR_SHOP_NOT_FOUND
```

Platform:

```text
RATE_LIMITED
INTERNAL_ERROR
```

---

# 82. Authorization Rule

Never authorize only based on role.

Object-level authorization is mandatory.

Customer:

```text
job.customer_id == current_user.id
```

Shop:

```text
job.shop.owner_id == current_user.id
```

Admin:

```text
role == ADMIN
```

Authorization must be enforced server-side.

---

# 83. Deny-by-Default Rule

Protected resources should be denied unless the authenticated principal explicitly has access.

Every request accessing:

- jobs
- documents
- shop resources
- audit information

must undergo authorization checks.

---

# 84. Rate Limits

Suggested Phase 1 limits:

```text
Login:
5/min/IP

Upload URL:
20/min/user

Job creation:
20/min/user

Nearby shops:
60/min/user
```

Return:

```text
429 TOO MANY REQUESTS
```

when exceeded.

---

# 85. CORS

Development:

```text
localhost frontend origins
```

Production:

```text
actual deployed frontend origins only
```

Do not use:

```text
*
```

for production authenticated API CORS.

---

# 86. API Endpoint Summary

## Authentication

```text
POST   /api/v1/auth/register
POST   /api/v1/auth/login
GET    /api/v1/auth/me
```

## Shops

```text
POST   /api/v1/shops
GET    /api/v1/shops/me
PATCH  /api/v1/shops/me
GET    /api/v1/shops/qr/{qr_token}
GET    /api/v1/shops/nearby
```

## Documents

```text
POST   /api/v1/documents/upload-url
POST   /api/v1/documents/{document_id}/complete
```

## Customer Jobs

```text
POST   /api/v1/jobs
GET    /api/v1/jobs
GET    /api/v1/jobs/{job_id}
POST   /api/v1/jobs/{job_id}/cancel
```

## Shop Jobs

```text
GET    /api/v1/shop/jobs
POST   /api/v1/shop/jobs/{job_id}/start
POST   /api/v1/shop/jobs/{job_id}/document-access
POST   /api/v1/shop/jobs/{job_id}/complete
POST   /api/v1/shop/jobs/{job_id}/fail
```

---

# 87. Backend Folder Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── dependencies.py
│   ├── db/
│   │   ├── session.py
│   │   └── base.py
│   ├── models/
│   │   ├── user.py
│   │   ├── shop.py
│   │   ├── document.py
│   │   ├── print_job.py
│   │   └── audit_log.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── shop.py
│   │   ├── document.py
│   │   └── job.py
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── shops.py
│   │       ├── documents.py
│   │       └── jobs.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── shop_service.py
│   │   ├── document_service.py
│   │   ├── job_service.py
│   │   ├── s3_service.py
│   │   └── audit_service.py
│   └── workers/
│       └── cleanup.py
├── alembic/
├── tests/
├── requirements.txt
└── .env.example
```

---

# 88. Web Folder Structure

```text
web/
├── src/
│   ├── api/
│   ├── components/
│   ├── layouts/
│   ├── pages/
│   │   ├── auth/
│   │   ├── customer/
│   │   └── shop/
│   ├── hooks/
│   ├── context/
│   ├── types/
│   ├── utils/
│   └── App.tsx
├── .env.example
└── package.json
```

---

# 89. Android Folder Structure

```text
mobile/
└── app/
    └── src/main/java/com/printshield/
        ├── data/
        │   ├── remote/
        │   ├── repository/
        │   └── model/
        ├── ui/
        │   ├── auth/
        │   ├── home/
        │   ├── shops/
        │   ├── scanner/
        │   ├── upload/
        │   └── jobs/
        └── navigation/
```

---

# 90. Environment Variables

Backend:

```text
DATABASE_URL=
JWT_SECRET=
JWT_ALGORITHM=
JWT_EXPIRE_MINUTES=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=
AWS_S3_BUCKET=
MAX_FILE_SIZE_MB=20
JOB_EXPIRY_MINUTES=60
PRESIGNED_URL_SECONDS=120
```

Never commit real `.env` files.

---

# 91. Customer Web Routes

```text
/auth/login
/auth/register
/
/shops
/shops/:id
/upload
/jobs
/jobs/:id
/profile
```

---

# 92. Shop Web Routes

```text
/shop/login
/shop/dashboard
/shop/queue
/shop/jobs/:id
/shop/profile
/shop/qr
```

---

# 93. Android Screens

```text
Splash
Login
Register
Home
Nearby Shops
Shop Details
QR Scanner
Document Picker
Print Configuration
Job Created
Job Details
Job History
Profile
```

---

# 94. Android Print Configuration

Keep the configuration simple:

```text
Selected document
Copies [ - 2 + ]
Send to Print
```

The app should not overwhelm ordinary users with advanced printer settings.

---

# 95. Frontend API Layer Rule

Web and Android must not scatter raw API URLs throughout UI components.

Use a dedicated service/API layer.

Conceptually:

```text
UI
 ↓
Repository / API Service
 ↓
REST API
```

This makes backend integration and contract changes easier.

---

# 96. OpenAPI Contract

FastAPI should expose the API through OpenAPI/Swagger.

Development documentation should be available through:

```text
/docs
```

The OpenAPI contract should be treated as the implementation reference for the web and mobile clients.

---

# 97. Database Migration Strategy

Use Alembic for schema migrations.

Do not manually modify production database structure without a migration.

Migration flow:

```text
Model change
   ↓
Alembic migration
   ↓
Review
   ↓
Apply
```

---

# 98. Testing Requirements

Backend tests must cover:

- registration
- login
- invalid password
- token expiry
- token validation
- cross-customer job access denial
- cross-shop job access denial
- shop creation
- shop update
- nearby shops
- QR resolution
- valid uploads
- invalid uploads
- oversized uploads
- job creation
- job cancellation
- job start
- job completion
- job failure
- job retry
- job expiry
- S3 behavior
- state transitions
- concurrent job start

---

# 99. End-to-End Test Cases

```text
E2E-001 Normal Print
E2E-002 Nearby Shop
E2E-003 QR Print
E2E-004 Cancel Job
E2E-005 Expired Job
E2E-006 Unauthorized Customer
E2E-007 Unauthorized Shop
E2E-008 Invalid File
E2E-009 Large File
E2E-010 Failed Print
```

---

# 100. Golden Path

The primary end-to-end flow is:

```text
Shop registers
      ↓
Shop location stored
      ↓
QR generated
      ↓
Customer finds shop
      ↓
Customer scans QR
      ↓
Customer uploads PDF
      ↓
Customer selects 2 copies
      ↓
Customer creates job
      ↓
Shop sees queue
      ↓
Shop starts job
      ↓
Shop requests document access
      ↓
Short-lived S3 URL issued
      ↓
Document printed
      ↓
Shop completes job
      ↓
Customer sees COMPLETED
      ↓
Access expires/revokes
      ↓
Temporary document is deleted
```

---

# 101. Shop Agent — Phase 1 Boundary

Actual automatic printer integration is **not required for Phase 1**.

A future lightweight Windows Shop Agent can integrate with the Windows Print Spooler.

Phase 1 can be tested using the Shop Web interface.

Do not block Phase 1 on printer hardware integration.

---

# 102. Queue Implementation

Phase 1 can use PostgreSQL as the application-backed queue.

A separate Redis/RabbitMQ/Kafka infrastructure is not required for the initial implementation.

Queue ordering:

```text
created_at ASC
```

---

# 103. API Integration Contract

All clients must use the same:

```text
base URL
API version
endpoint paths
request fields
response fields
status codes
error codes
authentication model
```

The frontend agents must not invent alternative endpoint names.

---

# 104. API Contract Change Rule

Once an endpoint is frozen, a client developer must not silently change:

```text
field name
field type
endpoint path
HTTP method
status meaning
enum value
response structure
```

A contract change must be communicated to all three team members.

---

# 105. Mock Development Strategy

Web and Android can work before backend endpoints are complete.

Use mock responses matching the exact API contract.

Example:

```json
{
  "data": {
    "shops": [
      {
        "id": "shop-001",
        "name": "Sri Lakshmi Xerox",
        "address": "Main Road",
        "distance_meters": 350,
        "is_open": true
      }
    ]
  }
}
```

When the backend becomes available, replace the mock implementation without changing the UI contract.

---

# 106. Git Repository Structure

Recommended single repository:

```text
PrintShield/
├── backend/
├── web/
├── mobile/
├── docs/
├── README.md
└── .gitignore
```

---

# 107. Git Branch Structure

Main branches:

```text
main
backend-dev
web-dev
mobile-dev
```

Feature branches:

```text
backend-auth
backend-shops
backend-documents
backend-jobs

web-auth
web-customer
web-shop

mobile-auth
mobile-qr
mobile-shops
mobile-jobs
```

Recommended flow:

```text
feature branch
      ↓
team branch
      ↓
main
```

---

# 108. Git Ownership

Backend member primarily owns:

```text
backend/**
```

Web member primarily owns:

```text
web/**
```

Mobile member primarily owns:

```text
mobile/**
```

Shared areas:

```text
docs/**
README.md
.gitignore
```

Avoid unnecessary simultaneous editing of shared files.

---

# 109. Git Commit Convention

Use commits such as:

```text
feat: add nearby shop API
feat: add customer job creation
feat: add QR scanner
feat: add shop queue
fix: prevent cross-shop job access
fix: validate PDF uploads
test: add job authorization tests
docs: update API contract
```

---

# 110. Team Development Workflow

Before starting work:

```bash
git checkout <team-branch>
git pull origin <team-branch>
git checkout -b <feature-branch>
```

After work:

```bash
git add .
git commit -m "feat: ..."
git push origin <feature-branch>
```

Then create a Pull Request into the team branch.

Example:

```text
backend-auth → backend-dev
```

After team-branch validation:

```text
backend-dev → main
```

---

# 111. Main Branch Rule

Do not directly push normal development work to:

```text
main
```

Main should represent the stable, integrated, deployable version.

---

# 112. Team Branch Synchronization

When `main` receives important changes, team branches should synchronize.

Example:

```bash
git checkout web-dev
git fetch origin
git merge origin/main
git push origin web-dev
```

This keeps the Web branch aligned with the latest integrated project.

---

# 113. Authorization Matrix

| Endpoint / Operation | Customer | Shop | Admin |
|---|---:|---:|---:|
| Register | ✓ | ✓ | — |
| Login | ✓ | ✓ | ✓ |
| Nearby shops | ✓ | ✓ | ✓ |
| QR resolution | ✓ | ✓ | ✓ |
| Create shop | — | ✓ | ✓ |
| Own shop | — | ✓ | ✓ |
| Upload document | ✓ | — | ✓* |
| Create job | ✓ | — | ✓* |
| Own jobs | ✓ | — | ✓ |
| Shop queue | — | ✓ | ✓ |
| Start job | — | ✓ | ✓ |
| Complete job | — | ✓ | ✓ |
| Fail job | — | ✓ | ✓ |
| Cancel own job | ✓ | — | ✓ |
| Audit logs | — | — | ✓ |

`✓*` represents administrative access only when explicitly implemented; normal Phase 1 customer ownership rules still apply.

---

# 114. Customer Web Responsibilities

The customer web client must support:

- registration
- login
- shop discovery
- nearby shops
- QR shop resolution
- document upload
- copy selection
- job creation
- job status
- job history
- cancellation
- profile

---

# 115. Shop Web Responsibilities

The shop web client must support:

- shop owner login
- shop dashboard
- queue display
- job details
- start job
- document access
- complete job
- fail job
- retry failed job
- shop profile
- QR display
- open/closed state

---

# 116. Android Responsibilities

Android must support:

- login
- registration
- home
- nearby shops
- QR scanner
- document picker
- Android Share target
- shop selection
- copy selection
- job creation
- job status
- job history
- profile

---

# 117. QR-to-Web/App Integration

A QR should resolve to a safe web URL.

If the Android application is installed, the same URL can later be associated with the app through Android App Links/deep linking.

This allows the same physical QR to support:

```text
QR
 ↓
Web
or
 ↓
Android app
```

without changing the shop QR itself.

---

# 118. S3 Security Requirements

The S3 bucket should be private.

Clients receive only short-lived presigned URLs.

Do not expose:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
```

to the web or Android client.

Use application-generated object keys.

---

# 119. S3 Lifecycle Backup

Configure an S3 lifecycle policy as a backup against unexpected leftover objects.

Application cleanup remains the primary lifecycle mechanism.

S3 lifecycle expiration is a secondary safety mechanism.

---

# 120. Sensitive Data Logging Rule

Never log:

```text
document contents
passwords
JWT tokens
AWS credentials
full private URLs
unnecessary identity information
```

Audit logs should record only the minimum operational information required.

---

# 121. API Validation

FastAPI/Pydantic should validate:

- required fields
- string lengths
- email format
- UUIDs
- enum values
- copy count
- latitude
- longitude
- radius
- limit
- file metadata

Validation errors should return a consistent API error format.

---

# 122. Shop Verification

The shop table includes:

```text
is_verified
```

Phase 1 can use this field to support administrative verification.

A future version may introduce a more advanced shop onboarding/verification workflow.

---

# 123. Shop Availability

The shop table includes:

```text
is_open
```

This represents whether the shop currently accepts jobs.

A closed shop should not receive new customer jobs.

The backend should enforce the active/open business rule rather than relying only on the frontend.

---

# 124. Job Expiration

Recommended default:

```text
JOB_EXPIRY_MINUTES=60
```

A job should not remain indefinitely in WAITING.

Expiration prevents stale documents and abandoned jobs from remaining active.

---

# 125. Document Expiration

Documents should have their own:

```text
expires_at
```

This allows the storage lifecycle to remain bounded even if a job is abandoned.

---

# 126. Database Transaction Rule

Operations that modify multiple related records should use appropriate database transactions.

Examples:

```text
Create job + audit log
Start job + audit log
Complete job + audit log
Cancel job + audit log
Fail job + audit log
Expire job + cleanup state
```

---

# 127. Job State Consistency

The backend must enforce valid transitions.

Do not allow:

```text
COMPLETED → PRINTING
CANCELLED → PRINTING
EXPIRED → PRINTING
COMPLETED → WAITING
```

unless a future specification explicitly introduces such transitions.

---

# 128. Cross-Object Security

Every document/job operation should verify the complete relationship chain.

Example:

```text
Authenticated shop owner
       ↓
owns shop
       ↓
shop owns job
       ↓
job references document
       ↓
document can be accessed
```

Do not authorize a document simply because a user knows its UUID.

---

# 129. UUID Usage

Use UUIDs for primary identifiers:

```text
users.id
shops.id
documents.id
print_jobs.id
audit_logs.id
```

This avoids exposing simple sequential identifiers for major resources.

---

# 130. Pickup Code Generation

Pickup codes should be generated server-side.

Recommended:

```text
4–6 digits
```

The database field is:

```text
VARCHAR(6)
```

The code should not be generated by trusting a client-supplied value.

---

# 131. Filename Handling

Preserve the original filename only as metadata:

```text
original_filename
```

Do not use the original filename as the S3 object key.

Generate a random storage filename/key.

---

# 132. File Size Handling

Reject files larger than:

```text
20 MB
```

Return:

```text
413 PAYLOAD TOO LARGE
```

where applicable.

The upload URL endpoint should reject obviously oversized files before generating a URL.

---

# 133. Document Checksum

Store:

```text
checksum_sha256 CHAR(64)
```

This can be used to identify the exact uploaded object and support integrity verification.

---

# 134. Shop Queue Isolation

A shop owner must see only:

```text
jobs.shop_id == their_shop.id
```

Never return another shop's queue.

Even if a malicious client modifies the `shop_id` query parameter, server-side authorization must reject the access.

---

# 135. Customer Job Isolation

A customer must see only:

```text
jobs.customer_id == current_user.id
```

Never rely on hiding other jobs in the UI.

The backend must enforce the filter.

---

# 136. Audit Log Isolation

Normal customers and shop owners must not be given unrestricted audit-log access.

Phase 1:

```text
ADMIN → audit logs
```

Only.

---

# 137. API Error Example

For an expired job:

HTTP:

```text
409 CONFLICT
```

or the endpoint-specific appropriate error status.

Body:

```json
{
  "error": {
    "code": "JOB_EXPIRED",
    "message": "This print job has expired."
  }
}
```

The exact status should remain consistent across implementation.

---

# 138. Backend Definition of Done

Backend Phase 1 is complete when:

- PostgreSQL is connected
- PostGIS is enabled
- all tables exist
- Alembic migrations work
- authentication works
- JWT authorization works
- shops work
- QR resolution works
- nearby shops work
- S3 presigned upload works
- document completion works
- jobs work
- queue works
- job state transitions are enforced
- document access works
- cleanup works
- audit logging works
- authorization tests pass
- OpenAPI is available
- `.env.example` is complete

---

# 139. Web Definition of Done

Web Phase 1 is complete when:

- customer authentication works
- shop discovery works
- nearby shops work
- QR flow works
- document upload works
- copy count works
- job creation works
- job tracking works
- customer history works
- customer cancellation works
- shop login works
- shop queue works
- shop job operations work
- API service layer is used
- responsive UI works

---

# 140. Android Definition of Done

Android Phase 1 is complete when:

- authentication works
- nearby shop permission flow works
- nearby shops work
- QR scanner works
- document picker works
- Android Share flow works
- shop selection works
- copy selection works
- job creation works
- job status works
- job history works
- profile works
- API service/repository architecture is used

---

# 141. Integration Definition of Done

The complete project is integrated when:

```text
Shop registration
        ↓
Shop location
        ↓
QR
        ↓
Customer discovery
        ↓
Document upload
        ↓
Job creation
        ↓
Shop queue
        ↓
Start
        ↓
Document access
        ↓
Print
        ↓
Complete
        ↓
Cleanup
```

works end-to-end through the real backend.

---

# 142. API Contract Freeze Rule

The following are considered frozen Phase 1 contract elements:

```text
endpoint paths
HTTP methods
request field names
request field types
response field names
response field types
status enums
role names
job status names
error codes
database relationship semantics
```

Any change must be discussed before implementation.

---

# 143. No Feature Creep Rule

Phase 1 should not be blocked by:

- advanced printer hardware
- automatic printer discovery
- payment processing
- complicated print settings
- continuous customer location tracking
- complex shop verification
- Redis/Kafka infrastructure
- WhatsApp API integration
- advanced analytics
- OCR
- document AI
- blockchain
- physical deletion guarantees

These can be future features.

---

# 144. Phase 1 Scope Boundary

The MVP is:

```text
Customer
   ↓
Choose/Scan Shop
   ↓
Upload Document
   ↓
Copies
   ↓
Create Job
   ↓
Shop Queue
   ↓
Temporary Document Access
   ↓
Print
   ↓
Complete
   ↓
Cleanup
```

---

# 145. Future Printer Integration

Future architecture:

```text
FastAPI
   ↓
Shop Agent
   ↓
Windows Print Spooler
   ↓
Physical Printer
```

The Shop Agent can run on the shop's Windows computer.

This is intentionally outside the first implementation milestone.

---

# 146. Future Mobile Expansion

The first web application can validate the complete product workflow.

The Android application can then connect to the same backend REST API.

No separate backend should be created for Android.

---

# 147. Single Backend Principle

Web and Android must use the same FastAPI backend.

```text
Customer Web ──┐
               ├── REST API → FastAPI
Android ───────┘
                    ↓
             PostgreSQL/PostGIS
                    ↓
                   S3
```

---

# 148. Database as Source of Truth

PostgreSQL is the source of truth for:

- users
- shops
- jobs
- document metadata
- status
- audit information

S3 is the source of truth for the actual document object.

---

# 149. Storage Separation

Do not store large document binaries in PostgreSQL.

Use:

```text
PostgreSQL → metadata
S3 → document object
```

This keeps the database focused on transactional data.

---

# 150. Shop QR Generation

When a shop is created:

1. generate a random UUID QR token
2. store it in `shops.qr_token`
3. generate the corresponding QR URL
4. display/download the QR in the shop dashboard

Example:

```text
https://printshield.app/shop/<qr_token>
```

---

# 151. QR Token Security

The QR token is an identifier, not a credential.

It should not directly grant access to documents.

The QR only resolves the shop.

Actual job/document access requires authenticated authorization.

---

# 152. Customer Location Permission

Android should request foreground location only when needed for:

```text
Nearby Shops
```

The application should explain why location is needed.

If denied:

```text
Nearby search unavailable
```

but:

```text
QR scanning still works
```

---

# 153. Location Privacy

PrintShield should not continuously collect customer location in Phase 1.

The backend receives:

```text
latitude
longitude
radius
limit
```

for a nearby-shop search.

The result is returned and the request can end.

---

# 154. Nearby Shop Distance

The API returns:

```text
distance_meters
```

This allows clients to display:

```text
350 m away
1.2 km away
```

without performing their own spatial calculations.

---

# 155. Shop Sorting

Nearby shops should be returned in ascending distance order.

Example:

```text
350 m
720 m
1.4 km
2.8 km
```

---

# 156. Shop Search Limits

The API should enforce a maximum:

```text
limit = 50
```

This prevents unnecessarily large result sets.

---

# 157. Cursor/Limit Strategy

Customer job lists should support pagination.

Phase 1 can use:

```text
limit
cursor
```

rather than returning an unlimited job history.

---

# 158. Shop Queue Limits

Shop queue requests should also use:

```text
limit
```

Example:

```http
GET /api/v1/shop/jobs?status=WAITING&limit=20
```

---

# 159. API Versioning

All Phase 1 APIs use:

```text
/api/v1/
```

Do not create unversioned production endpoints such as:

```text
/api/jobs
```

The version prefix allows future API evolution.

---

# 160. Content Type

JSON endpoints use:

```http
Content-Type: application/json
```

File uploads to S3 use the appropriate object content type specified by the presigned upload process.

---

# 161. Authentication Failure Handling

Invalid credentials should not reveal whether an email exists.

Use a generic authentication error:

```text
AUTH_INVALID_CREDENTIALS
```

Avoid account enumeration through login responses.

---

# 162. Inactive User Handling

If:

```text
users.is_active = false
```

the user should not be permitted to perform normal authenticated operations.

Return an appropriate authorization/authentication error.

---

# 163. Inactive Shop Handling

If:

```text
shops.is_open = false
```

new customer jobs should not be accepted for that shop.

Existing jobs may continue according to the job lifecycle rules.

---

# 164. Shop Ownership

A shop owner can modify only their own shop.

The backend must derive the shop from the authenticated identity rather than trusting an arbitrary owner ID supplied by the client.

---

# 165. Admin Access

Admin access should be explicit.

The frontend must not be the security boundary.

Backend dependencies should enforce the required role.

---

# 166. Dependency Structure

FastAPI dependencies should provide concepts such as:

```text
get_current_user()
require_customer()
require_shop_owner()
require_admin()
```

Object ownership must then be checked inside the resource/service layer.

---

# 167. Service Layer Rule

Routes should not contain all business logic.

Recommended:

```text
Router
  ↓
Service
  ↓
Repository/ORM
  ↓
Database
```

S3 operations should be isolated inside:

```text
s3_service.py
```

---

# 168. Audit Service Rule

Audit logging should be centralized through:

```text
audit_service.py
```

This prevents every endpoint from implementing inconsistent audit behavior.

---

# 169. Cleanup Worker Rule

Cleanup logic should be isolated in:

```text
workers/cleanup.py
```

It should handle:

- expired jobs
- expired documents
- S3 cleanup
- document deletion timestamps

---

# 170. Database Constraint Strategy

Use database constraints where practical.

Examples:

```text
users.email UNIQUE
shops.qr_token UNIQUE
documents.storage_key UNIQUE
print_jobs.document_id UNIQUE
```

Application validation should complement database constraints.

---

# 171. One Document per Job

Phase 1 models:

```text
print_jobs.document_id UNIQUE
```

Therefore:

```text
one print job = one document
```

Multiple copies are represented by:

```text
copy_count
```

not by duplicating the document record.

---

# 172. One Shop per Job

Each job contains:

```text
shop_id
```

A job belongs to exactly one shop.

---

# 173. Customer-to-Document Relationship

A customer may own multiple document records over time.

```text
users 1 → N documents
```

Documents are temporary and should be cleaned after lifecycle completion.

---

# 174. Job-to-Audit Relationship

A job may have multiple audit events:

```text
JOB_CREATED
JOB_STARTED
JOB_FAILED
JOB_STARTED
JOB_COMPLETED
DOCUMENT_DELETED
```

Therefore:

```text
print_jobs 1 → N audit_logs
```

---

# 175. Example Audit Timeline

```text
09:30 USER_REGISTERED
09:35 SHOP_CREATED
09:42 QR_ACCESSED
09:43 DOCUMENT_UPLOADED
09:44 JOB_CREATED
09:45 JOB_STARTED
09:46 DOCUMENT_ACCESS
09:48 JOB_COMPLETED
09:48 DOCUMENT_DELETED
```

Only safe operational metadata should be retained.

---

# 176. Failed Print Example

```text
WAITING
   ↓
PRINTING
   ↓
FAILED
```

Reason:

```json
{
  "reason": "Printer out of paper"
}
```

The shop can retry:

```text
FAILED → PRINTING
```

provided the job is still valid.

---

# 177. Expired Job Example

```text
WAITING
   ↓
expires_at reached
   ↓
EXPIRED
   ↓
document cleanup
```

A customer cannot cancel an already expired job.

---

# 178. Cancelled Job Example

```text
WAITING
   ↓
Customer cancels
   ↓
CANCELLED
   ↓
document cleanup
```

A cancelled job cannot be restarted.

---

# 179. Completed Job Example

```text
PRINTING
   ↓
Shop completes
   ↓
COMPLETED
   ↓
document cleanup
```

Completed jobs remain available as metadata/history.

The actual document should no longer remain accessible.

---

# 180. Post-Completion Access Rule

After:

```text
COMPLETED
```

the shop must not be able to request a new document-access URL.

Likewise:

```text
CANCELLED
EXPIRED
```

must not provide document access.

---

# 181. Post-Expiry Access Rule

If:

```text
expires_at < now
```

document access must be denied even if the job status has not yet been asynchronously updated.

This protects against a timing gap between expiration and cleanup worker execution.

---

# 182. Job Status Revalidation

Every sensitive job operation should re-check current database state.

Do not rely on stale frontend state.

---

# 183. Document Access Revalidation

Before generating a presigned document URL:

```text
authenticated user
        ↓
shop ownership
        ↓
job ownership
        ↓
PRINTING status
        ↓
not expired
        ↓
document exists
        ↓
generate short-lived URL
```

---

# 184. S3 URL Revalidation

The application should generate presigned URLs only after authorization.

A user must not be able to construct an S3 URL manually and bypass application authorization.

---

# 185. S3 Bucket Access

The application backend should hold the AWS permissions necessary to generate presigned URLs and manage objects.

Clients should never receive AWS secret credentials.

---

# 186. Production Secret Management

For development:

```text
.env
```

For production, use an appropriate secret-management mechanism/environment configuration.

Never commit:

```text
JWT_SECRET
AWS_SECRET_ACCESS_KEY
DATABASE_PASSWORD
```

to Git.

---

# 187. Environment Example

Provide:

```text
.env.example
```

with blank values:

```text
DATABASE_URL=
JWT_SECRET=
JWT_ALGORITHM=
JWT_EXPIRE_MINUTES=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=
AWS_S3_BUCKET=
MAX_FILE_SIZE_MB=20
JOB_EXPIRY_MINUTES=60
PRESIGNED_URL_SECONDS=120
```

---

# 188. Testing Authorization

At minimum test:

```text
Customer A cannot access Customer B job
Customer A cannot access Customer B document
Shop A cannot access Shop B job
Shop A cannot access Shop B document
Customer cannot start shop job
Customer cannot complete shop job
Shop owner cannot read admin audit logs
```

---

# 189. Testing State Transitions

Test both valid and invalid transitions.

Valid:

```text
CREATED → WAITING
WAITING → PRINTING
PRINTING → COMPLETED
PRINTING → FAILED
FAILED → PRINTING
WAITING → CANCELLED
WAITING → EXPIRED
```

Invalid:

```text
COMPLETED → PRINTING
CANCELLED → PRINTING
EXPIRED → PRINTING
COMPLETED → WAITING
```

---

# 190. Testing Concurrency

Simulate two simultaneous:

```text
POST /api/v1/shop/jobs/{job_id}/start
```

Only one request should successfully transition:

```text
WAITING → PRINTING
```

The other should receive an appropriate conflict/state error.

---

# 191. Testing File Security

Test:

```text
valid PDF
valid JPG
valid PNG
unsupported EXE
fake extension
oversized file
invalid MIME
invalid file signature
missing S3 object
expired upload
```

---

# 192. Testing Nearby Shops

Test:

```text
valid latitude
valid longitude
radius too small
radius too large
invalid latitude
invalid longitude
invalid limit
no shops
multiple shops
distance ordering
```

---

# 193. Testing QR

Test:

```text
valid QR token
invalid UUID
nonexistent token
closed shop
verified/unverified shop
safe response fields
```

---

# 194. Testing Cleanup

Test:

```text
completed job → document deleted
cancelled job → document deleted
expired job → document deleted
failed job → document retained while retry is possible
```

---

# 195. Customer Golden Path Test

```text
Register
 ↓
Login
 ↓
Find nearby shop
 ↓
Select shop
 ↓
Upload PDF
 ↓
Complete upload
 ↓
Create job
 ↓
View WAITING
 ↓
Shop starts
 ↓
Shop accesses document
 ↓
Shop completes
 ↓
Customer sees COMPLETED
 ↓
Document unavailable
```

---

# 196. QR Golden Path Test

```text
Open QR
 ↓
Resolve shop
 ↓
Confirm shop
 ↓
Select document
 ↓
Copies
 ↓
Create job
 ↓
Shop queue
```

---

# 197. Android Share Golden Path

```text
Android Files
 ↓
Share
 ↓
PrintShield
 ↓
Select/confirm shop
 ↓
Copies
 ↓
Send
 ↓
Job created
```

---

# 198. Web-Shop Golden Path

```text
Shop Login
 ↓
Dashboard
 ↓
Waiting Queue
 ↓
Open Job
 ↓
Start
 ↓
Document Access
 ↓
Print
 ↓
Complete
 ↓
Queue updates
```

---

# 199. Integration Responsibility

The three development streams are:

```text
Backend API
Web Application
Android Application
```

All three must follow this document as the shared contract.

---

# 200. Final Phase 1 Architecture

```text
                         CUSTOMER
                            │
              ┌─────────────┴─────────────┐
              │                           │
        Customer Web                Customer Mobile
              │                           │
              └─────────────┬─────────────┘
                            │
                         REST API
                            │
                    ┌───────▼───────┐
                    │    FastAPI    │
                    │    Backend    │
                    └───────┬───────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
     PostgreSQL          AWS S3          Job Manager
     + PostGIS           Documents        / Queue
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                            ▼
                       SHOP ACCOUNT
                            │
                       Shop Web App
                            │
                     Later Shop Agent
                            │
                            ▼
                         PRINTER
```

---

# 201. Final API Contract Principle

The backend is the source of truth for API behavior.

The web and mobile clients must implement this contract exactly.

If a client needs a new field or endpoint:

```text
request change
      ↓
team discussion
      ↓
contract update
      ↓
backend
      ↓
web + mobile
```

Do not silently fork the API contract.

---

# 202. Final Product Principle

PrintShield is not trying to promise that a printer shop can never physically copy a document.

It is designed to change the normal workflow from:

```text
Customer
   ↓
Send reusable document
   ↓
Shop keeps file
```

to:

```text
Customer
   ↓
Temporary Print Job
   ↓
Controlled Shop Access
   ↓
Print
   ↓
Complete
   ↓
Cleanup
```

That is the core privacy improvement.

---

# 203. Final Phase 1 Scope

Phase 1 is complete when the system can reliably perform:

```text
REGISTER
LOGIN
SHOP REGISTRATION
SHOP LOCATION
QR RESOLUTION
NEARBY SHOP DISCOVERY
DOCUMENT UPLOAD
DOCUMENT VALIDATION
PRINT JOB CREATION
CUSTOMER JOB HISTORY
CUSTOMER CANCELLATION
SHOP QUEUE
JOB START
TEMPORARY DOCUMENT ACCESS
JOB COMPLETE
JOB FAIL
JOB RETRY
JOB EXPIRY
DOCUMENT CLEANUP
AUDIT LOGGING
ROLE AUTHORIZATION
OBJECT-LEVEL AUTHORIZATION
```

---

# 204. Final Frozen Contract

This document should be treated as the **PrintShield Phase 1 API + Database + Integration Single Source of Truth**.

Before implementation, the three agents should align with:

```text
Backend → implements the contract
Web     → consumes the contract
Mobile  → consumes the contract
```

No agent should independently redesign the core API, database relationships, job state machine, or authorization model.

---

# 205. Implementation Order

Recommended backend order:

```text
1. Project setup
2. PostgreSQL/PostGIS
3. SQLAlchemy models
4. Alembic
5. Authentication
6. Shop APIs
7. Nearby shop API
8. QR API
9. S3 service
10. Document APIs
11. Job APIs
12. Shop queue
13. Job state transitions
14. Audit logging
15. Cleanup worker
16. Tests
17. OpenAPI verification
```

Recommended Web order:

```text
1. Project setup
2. API client
3. Auth
4. Customer layout
5. Shop discovery
6. QR route
7. Upload
8. Job creation
9. Customer jobs
10. Shop dashboard
11. Shop queue
12. Job operations
13. Polish/testing
```

Recommended Android order:

```text
1. Project setup
2. API client
3. Auth
4. Home
5. Nearby shops
6. QR scanner
7. Document picker
8. Share target
9. Print configuration
10. Job creation
11. Job status
12. Job history
13. Profile
14. Integration testing
```

---

# 206. Final Integration Checklist

Before declaring Phase 1 complete:

```text
[ ] Backend starts successfully
[ ] PostgreSQL connected
[ ] PostGIS enabled
[ ] Alembic migrations applied
[ ] User registration works
[ ] Login works
[ ] JWT authorization works
[ ] Shop registration works
[ ] Shop location stored
[ ] Nearby shop search works
[ ] QR resolution works
[ ] S3 bucket private
[ ] Presigned upload works
[ ] Document completion works
[ ] File restrictions enforced
[ ] Job creation works
[ ] Customer job list works
[ ] Customer cancellation works
[ ] Shop queue works
[ ] Job start is atomic
[ ] Document access is temporary
[ ] Complete works
[ ] Fail works
[ ] Retry works
[ ] Expiry works
[ ] Cleanup works
[ ] Audit logs work
[ ] Cross-customer access denied
[ ] Cross-shop access denied
[ ] API errors follow contract
[ ] Web integrated
[ ] Android integrated
[ ] E2E golden path passes
[ ] No secrets committed
[ ] Production CORS restricted
[ ] OpenAPI verified
```

---

# 207. Final Engineering Rule

When there is uncertainty during implementation, prefer the existing contract over inventing a new behavior.

The contract is intentionally designed so that:

```text
one backend
+
one database
+
one private storage layer
+
one print-job state machine
+
one authorization model
+
two customer clients
+
one shop client
```

can evolve into the full PrintShield product without rebuilding the foundation.

---

# 208. End of Phase 1 Specification

**PrintShield Phase 1 — Frozen Engineering Contract**

**Primary slogan:**

> **Don’t give the shop your document. Give them temporary permission to print it.**

**Architecture:**

```text
Customer Web
      │
Android Mobile
      │
      ▼
FastAPI REST API
      │
 ┌────┼───────────────┐
 ▼    ▼               ▼
Postgres/PostGIS     S3      Job Lifecycle
      │               │
      └───────┬───────┘
              ▼
          Shop Web
              │
              ▼
        Physical Printer
```

**Phase 1 objective:**

```text
Scan → Upload → Copies → Send → Collect
```

with controlled access, temporary storage, shop isolation, customer isolation, job lifecycle management, auditability, and a shared API contract for all three development streams.
