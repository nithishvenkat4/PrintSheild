import pytest
from app.core.exceptions import ErrorCode


def test_concurrent_job_start_idempotency(client, customer_headers, shop_owner_headers, registered_shop, uploaded_document):
    create_res = client.post(
        "/api/v1/jobs",
        headers=customer_headers,
        json={"shop_id": str(registered_shop.id), "document_id": str(uploaded_document.id), "copy_count": 1}
    )
    job_id = create_res.json()["data"]["id"]

    # First start attempt succeeds
    first_res = client.post(f"/api/v1/shop/jobs/{job_id}/start", headers=shop_owner_headers)
    assert first_res.status_code == 200
    assert first_res.json()["data"]["status"] == "PRINTING"

    # Second start attempt on already printing job must fail with 409
    second_res = client.post(f"/api/v1/shop/jobs/{job_id}/start", headers=shop_owner_headers)
    assert second_res.status_code == 409
    assert second_res.json()["error"]["code"] == ErrorCode.JOB_ALREADY_PRINTING


def test_concurrent_complete_idempotency(client, customer_headers, shop_owner_headers, registered_shop, uploaded_document):
    create_res = client.post(
        "/api/v1/jobs",
        headers=customer_headers,
        json={"shop_id": str(registered_shop.id), "document_id": str(uploaded_document.id), "copy_count": 1}
    )
    job_id = create_res.json()["data"]["id"]

    client.post(f"/api/v1/shop/jobs/{job_id}/start", headers=shop_owner_headers)

    # First complete attempt succeeds
    first_res = client.post(f"/api/v1/shop/jobs/{job_id}/complete", headers=shop_owner_headers)
    assert first_res.status_code == 200
    assert first_res.json()["data"]["status"] == "COMPLETED"

    # Second complete attempt must fail with 409 (already COMPLETED)
    second_res = client.post(f"/api/v1/shop/jobs/{job_id}/complete", headers=shop_owner_headers)
    assert second_res.status_code == 409
    assert second_res.json()["error"]["code"] == ErrorCode.JOB_INVALID_STATE
