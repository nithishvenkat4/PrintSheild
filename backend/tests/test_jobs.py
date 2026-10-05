import uuid
import pytest
from app.models.print_job import PrintJob, PrintJobStatus
from app.core.exceptions import ErrorCode


def test_create_job_success(client, customer_headers, registered_shop, uploaded_document):
    response = client.post(
        "/api/v1/jobs",
        headers=customer_headers,
        json={
            "shop_id": str(registered_shop.id),
            "document_id": str(uploaded_document.id),
            "copy_count": 2
        }
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["status"] == "WAITING"
    assert data["copy_count"] == 2
    assert len(data["pickup_code"]) == 4
    assert data["shop"]["name"] == registered_shop.name
    assert data["document"]["filename"] == uploaded_document.original_filename


def test_create_job_invalid_copy_count(client, customer_headers, registered_shop, uploaded_document):
    response = client.post(
        "/api/v1/jobs",
        headers=customer_headers,
        json={
            "shop_id": str(registered_shop.id),
            "document_id": str(uploaded_document.id),
            "copy_count": 0  # Below 1
        }
    )
    assert response.status_code in (400, 422)

    response2 = client.post(
        "/api/v1/jobs",
        headers=customer_headers,
        json={
            "shop_id": str(registered_shop.id),
            "document_id": str(uploaded_document.id),
            "copy_count": 25  # Above 20
        }
    )
    assert response2.status_code in (400, 422)


def test_create_job_inactive_shop(client, customer_headers, registered_shop, uploaded_document, db):
    registered_shop.is_open = False
    db.commit()

    response = client.post(
        "/api/v1/jobs",
        headers=customer_headers,
        json={
            "shop_id": str(registered_shop.id),
            "document_id": str(uploaded_document.id),
            "copy_count": 1
        }
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == ErrorCode.SHOP_INACTIVE


def test_create_job_document_not_found(client, customer_headers, registered_shop):
    fake_doc_id = uuid.uuid4()
    response = client.post(
        "/api/v1/jobs",
        headers=customer_headers,
        json={
            "shop_id": str(registered_shop.id),
            "document_id": str(fake_doc_id),
            "copy_count": 1
        }
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == ErrorCode.DOCUMENT_NOT_FOUND


def test_get_customer_jobs_list(client, customer_headers, registered_shop, uploaded_document):
    # Create a job first
    client.post(
        "/api/v1/jobs",
        headers=customer_headers,
        json={
            "shop_id": str(registered_shop.id),
            "document_id": str(uploaded_document.id),
            "copy_count": 1
        }
    )
    response = client.get("/api/v1/jobs", headers=customer_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["jobs"]) >= 1


def test_get_job_detail_customer(client, customer_headers, registered_shop, uploaded_document):
    create_res = client.post(
        "/api/v1/jobs",
        headers=customer_headers,
        json={
            "shop_id": str(registered_shop.id),
            "document_id": str(uploaded_document.id),
            "copy_count": 3
        }
    )
    job_id = create_res.json()["data"]["id"]

    response = client.get(f"/api/v1/jobs/{job_id}", headers=customer_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == job_id
    assert data["copy_count"] == 3


def test_cancel_job_while_waiting(client, customer_headers, registered_shop, uploaded_document):
    create_res = client.post(
        "/api/v1/jobs",
        headers=customer_headers,
        json={
            "shop_id": str(registered_shop.id),
            "document_id": str(uploaded_document.id),
            "copy_count": 2
        }
    )
    job_id = create_res.json()["data"]["id"]

    cancel_res = client.post(f"/api/v1/jobs/{job_id}/cancel", headers=customer_headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["data"]["status"] == "CANCELLED"

    # Verify status changed on detail query
    get_res = client.get(f"/api/v1/jobs/{job_id}", headers=customer_headers)
    assert get_res.json()["data"]["status"] == "CANCELLED"


def test_cancel_job_while_printing_fails(client, customer_headers, shop_owner_headers, registered_shop, uploaded_document):
    create_res = client.post(
        "/api/v1/jobs",
        headers=customer_headers,
        json={
            "shop_id": str(registered_shop.id),
            "document_id": str(uploaded_document.id),
            "copy_count": 1
        }
    )
    job_id = create_res.json()["data"]["id"]

    # Shop starts printing
    start_res = client.post(f"/api/v1/shop/jobs/{job_id}/start", headers=shop_owner_headers)
    assert start_res.status_code == 200

    # Customer tries to cancel while PRINTING
    cancel_res = client.post(f"/api/v1/jobs/{job_id}/cancel", headers=customer_headers)
    assert cancel_res.status_code == 409
    assert cancel_res.json()["error"]["code"] == ErrorCode.JOB_CANNOT_CANCEL
