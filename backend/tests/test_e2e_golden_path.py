import pytest
from app.core.exceptions import ErrorCode


def test_full_golden_path_e2e(client):
    """
    End-to-End Golden Path Test according to Phase 1 Specification (Section 100):
    1. Customer Registration & Login
    2. Shop Owner Registration & Login
    3. Shop Owner registers shop & gets QR code
    4. Customer discovers/resolves shop via QR
    5. Customer requests upload URL & completes upload
    6. Customer creates 2-copy print job
    7. Shop Owner sees job in queue
    8. Shop Owner starts job (WAITING -> PRINTING)
    9. Shop Owner gets 120s document download access
    10. Shop Owner completes job (PRINTING -> COMPLETED)
    11. S3 document is deleted, post-completion document access is denied
    """
    # 1. Customer Registration & Login
    cust_reg = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Kavitha Customer",
            "email": "kavitha_golden@example.com",
            "password": "GoldenPassword@123",
            "role": "CUSTOMER"
        }
    )
    assert cust_reg.status_code == 201

    cust_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "kavitha_golden@example.com",
            "password": "GoldenPassword@123"
        }
    )
    assert cust_login.status_code == 200
    customer_token = cust_login.json()["data"]["access_token"]
    cust_headers = {"Authorization": f"Bearer {customer_token}"}

    # 2. Shop Owner Registration & Login
    shop_reg = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Murugan Shopkeeper",
            "email": "murugan_golden@example.com",
            "password": "GoldenPassword@123",
            "role": "SHOP_OWNER"
        }
    )
    assert shop_reg.status_code == 201

    shop_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "murugan_golden@example.com",
            "password": "GoldenPassword@123"
        }
    )
    assert shop_login.status_code == 200
    shop_token = shop_login.json()["data"]["access_token"]
    shop_headers = {"Authorization": f"Bearer {shop_token}"}

    # 3. Shop Owner registers shop
    create_shop_res = client.post(
        "/api/v1/shops",
        headers=shop_headers,
        json={
            "name": "Murugan Xerox Corner",
            "phone": "+919840012345",
            "address": "100 South Usman Road, Chennai",
            "latitude": 13.0380,
            "longitude": 80.2335
        }
    )
    assert create_shop_res.status_code == 201
    shop_data = create_shop_res.json()["data"]
    shop_id = shop_data["id"]
    qr_token = shop_data["qr_token"]

    # 4. Customer resolves shop via QR code
    qr_res = client.get(f"/api/v1/shops/qr/{qr_token}")
    assert qr_res.status_code == 200
    assert qr_res.json()["data"]["shop_id"] == shop_id
    assert qr_res.json()["data"]["name"] == "Murugan Xerox Corner"

    # 5. Customer uploads document
    upload_url_res = client.post(
        "/api/v1/documents/upload-url",
        headers=cust_headers,
        json={
            "filename": "tax_invoice_2026.pdf",
            "mime_type": "application/pdf",
            "file_size": 185400
        }
    )
    assert upload_url_res.status_code == 200
    doc_id = upload_url_res.json()["data"]["document_id"]
    assert "upload_url" in upload_url_res.json()["data"]

    complete_res = client.post(f"/api/v1/documents/{doc_id}/complete", headers=cust_headers)
    assert complete_res.status_code == 200
    assert complete_res.json()["data"]["status"] == "AVAILABLE"

    # 6. Customer creates Print Job
    job_create_res = client.post(
        "/api/v1/jobs",
        headers=cust_headers,
        json={
            "shop_id": shop_id,
            "document_id": doc_id,
            "copy_count": 2
        }
    )
    assert job_create_res.status_code == 201
    job_data = job_create_res.json()["data"]
    job_id = job_data["id"]
    pickup_code = job_data["pickup_code"]
    assert job_data["status"] == "WAITING"
    assert job_data["copy_count"] == 2
    assert len(pickup_code) == 4

    # 7. Shop Owner sees job in Queue
    queue_res = client.get("/api/v1/shop/jobs", headers=shop_headers)
    assert queue_res.status_code == 200
    queue = queue_res.json()["data"]["jobs"]
    matching_job = next((j for j in queue if j["id"] == job_id), None)
    assert matching_job is not None
    assert matching_job["pickup_code"] == pickup_code
    assert matching_job["filename"] == "tax_invoice_2026.pdf"

    # 8. Shop Owner starts the job (WAITING -> PRINTING)
    start_res = client.post(f"/api/v1/shop/jobs/{job_id}/start", headers=shop_headers)
    assert start_res.status_code == 200
    assert start_res.json()["data"]["status"] == "PRINTING"

    # 9. Shop Owner requests temporary document access
    access_res = client.post(f"/api/v1/shop/jobs/{job_id}/document-access", headers=shop_headers)
    assert access_res.status_code == 200
    assert "download_url" in access_res.json()["data"]
    assert access_res.json()["data"]["expires_in"] == 120

    # 10. Shop Owner completes the job (PRINTING -> COMPLETED)
    complete_job_res = client.post(f"/api/v1/shop/jobs/{job_id}/complete", headers=shop_headers)
    assert complete_job_res.status_code == 200
    assert complete_job_res.json()["data"]["status"] == "COMPLETED"

    # 11. Post-completion: Document access is revoked
    revoked_access_res = client.post(f"/api/v1/shop/jobs/{job_id}/document-access", headers=shop_headers)
    assert revoked_access_res.status_code == 409
    assert revoked_access_res.json()["error"]["code"] == ErrorCode.JOB_INVALID_STATE

    # Verify Customer's job status is now COMPLETED
    customer_job_res = client.get(f"/api/v1/jobs/{job_id}", headers=cust_headers)
    assert customer_job_res.status_code == 200
    assert customer_job_res.json()["data"]["status"] == "COMPLETED"
