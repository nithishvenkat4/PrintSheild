import uuid
import pytest
from app.core.exceptions import ErrorCode


def test_shop_queue_fifo_order(client, customer_headers, shop_owner_headers, registered_shop, db, customer_user):
    from app.models.document import Document
    from datetime import datetime, timezone, timedelta

    # Create two documents
    doc1 = Document(
        id=uuid.uuid4(),
        owner_id=customer_user.id,
        original_filename="doc1.pdf",
        storage_key=f"jobs/{uuid.uuid4()}/doc1.pdf",
        mime_type="application/pdf",
        file_size=1000,
        checksum_sha256="0" * 64,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=60)
    )
    doc2 = Document(
        id=uuid.uuid4(),
        owner_id=customer_user.id,
        original_filename="doc2.pdf",
        storage_key=f"jobs/{uuid.uuid4()}/doc2.pdf",
        mime_type="application/pdf",
        file_size=2000,
        checksum_sha256="0" * 64,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=60)
    )
    db.add_all([doc1, doc2])
    db.commit()

    # Create two jobs
    client.post(
        "/api/v1/jobs",
        headers=customer_headers,
        json={"shop_id": str(registered_shop.id), "document_id": str(doc1.id), "copy_count": 1}
    )
    client.post(
        "/api/v1/jobs",
        headers=customer_headers,
        json={"shop_id": str(registered_shop.id), "document_id": str(doc2.id), "copy_count": 2}
    )

    # Fetch shop queue
    queue_res = client.get("/api/v1/shop/jobs", headers=shop_owner_headers)
    assert queue_res.status_code == 200
    data = queue_res.json()["data"]["jobs"]
    assert len(data) >= 2
    assert data[0]["filename"] == "doc1.pdf"
    assert data[1]["filename"] == "doc2.pdf"


def test_shop_start_job(client, customer_headers, shop_owner_headers, registered_shop, uploaded_document):
    create_res = client.post(
        "/api/v1/jobs",
        headers=customer_headers,
        json={"shop_id": str(registered_shop.id), "document_id": str(uploaded_document.id), "copy_count": 1}
    )
    job_id = create_res.json()["data"]["id"]

    start_res = client.post(f"/api/v1/shop/jobs/{job_id}/start", headers=shop_owner_headers)
    assert start_res.status_code == 200
    data = start_res.json()["data"]
    assert data["status"] == "PRINTING"
    assert "started_at" in data


def test_shop_get_document_access_while_printing(client, customer_headers, shop_owner_headers, registered_shop, uploaded_document):
    create_res = client.post(
        "/api/v1/jobs",
        headers=customer_headers,
        json={"shop_id": str(registered_shop.id), "document_id": str(uploaded_document.id), "copy_count": 1}
    )
    job_id = create_res.json()["data"]["id"]

    # Start printing
    client.post(f"/api/v1/shop/jobs/{job_id}/start", headers=shop_owner_headers)

    # Request document access
    access_res = client.post(f"/api/v1/shop/jobs/{job_id}/document-access", headers=shop_owner_headers)
    assert access_res.status_code == 200
    data = access_res.json()["data"]
    assert "download_url" in data
    assert data["expires_in"] == 120


def test_shop_get_document_access_before_printing_fails(client, customer_headers, shop_owner_headers, registered_shop, uploaded_document):
    create_res = client.post(
        "/api/v1/jobs",
        headers=customer_headers,
        json={"shop_id": str(registered_shop.id), "document_id": str(uploaded_document.id), "copy_count": 1}
    )
    job_id = create_res.json()["data"]["id"]

    # Request access while still WAITING
    access_res = client.post(f"/api/v1/shop/jobs/{job_id}/document-access", headers=shop_owner_headers)
    assert access_res.status_code == 409
    assert access_res.json()["error"]["code"] == ErrorCode.JOB_INVALID_STATE


def test_shop_complete_job(client, customer_headers, shop_owner_headers, registered_shop, uploaded_document):
    create_res = client.post(
        "/api/v1/jobs",
        headers=customer_headers,
        json={"shop_id": str(registered_shop.id), "document_id": str(uploaded_document.id), "copy_count": 1}
    )
    job_id = create_res.json()["data"]["id"]

    client.post(f"/api/v1/shop/jobs/{job_id}/start", headers=shop_owner_headers)

    complete_res = client.post(f"/api/v1/shop/jobs/{job_id}/complete", headers=shop_owner_headers)
    assert complete_res.status_code == 200
    assert complete_res.json()["data"]["status"] == "COMPLETED"


def test_shop_fail_and_retry_job(client, customer_headers, shop_owner_headers, registered_shop, uploaded_document):
    create_res = client.post(
        "/api/v1/jobs",
        headers=customer_headers,
        json={"shop_id": str(registered_shop.id), "document_id": str(uploaded_document.id), "copy_count": 1}
    )
    job_id = create_res.json()["data"]["id"]

    client.post(f"/api/v1/shop/jobs/{job_id}/start", headers=shop_owner_headers)

    fail_res = client.post(
        f"/api/v1/shop/jobs/{job_id}/fail",
        headers=shop_owner_headers,
        json={"reason": "Paper jam occurred"}
    )
    assert fail_res.status_code == 200
    assert fail_res.json()["data"]["status"] == "FAILED"
    assert fail_res.json()["data"]["failure_reason"] == "Paper jam occurred"

    # Retry failed job (FAILED -> PRINTING)
    retry_res = client.post(f"/api/v1/shop/jobs/{job_id}/start", headers=shop_owner_headers)
    assert retry_res.status_code == 200
    assert retry_res.json()["data"]["status"] == "PRINTING"
