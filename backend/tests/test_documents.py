import uuid
import pytest
from app.core.exceptions import ErrorCode


def test_create_upload_url_pdf(client, customer_headers):
    response = client.post(
        "/api/v1/documents/upload-url",
        headers=customer_headers,
        json={
            "filename": "college_certificate.pdf",
            "mime_type": "application/pdf",
            "file_size": 1024 * 500  # 500 KB
        }
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "document_id" in data
    assert "upload_url" in data
    assert data["expires_in"] == 300


def test_create_upload_url_jpeg(client, customer_headers):
    response = client.post(
        "/api/v1/documents/upload-url",
        headers=customer_headers,
        json={
            "filename": "passport_photo.jpeg",
            "mime_type": "image/jpeg",
            "file_size": 1024 * 200
        }
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "document_id" in data


def test_create_upload_url_unsupported_file_type(client, customer_headers):
    response = client.post(
        "/api/v1/documents/upload-url",
        headers=customer_headers,
        json={
            "filename": "malicious_script.exe",
            "mime_type": "application/x-msdownload",
            "file_size": 1024
        }
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == ErrorCode.DOCUMENT_INVALID_TYPE


def test_create_upload_url_oversized_file(client, customer_headers):
    response = client.post(
        "/api/v1/documents/upload-url",
        headers=customer_headers,
        json={
            "filename": "giant_poster.pdf",
            "mime_type": "application/pdf",
            "file_size": 25 * 1024 * 1024  # 25 MB (exceeds 20MB limit)
        }
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == ErrorCode.DOCUMENT_TOO_LARGE


def test_complete_upload_success(client, customer_headers, uploaded_document):
    response = client.post(
        f"/api/v1/documents/{uploaded_document.id}/complete",
        headers=customer_headers
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["document_id"] == str(uploaded_document.id)
    assert data["status"] == "AVAILABLE"
    assert data["filename"] == uploaded_document.original_filename


def test_complete_upload_nonexistent_document(client, customer_headers):
    fake_id = uuid.uuid4()
    response = client.post(
        f"/api/v1/documents/{fake_id}/complete",
        headers=customer_headers
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == ErrorCode.DOCUMENT_NOT_FOUND


def test_complete_upload_different_customer_forbidden(client, uploaded_document, db):
    from app.models.user import User, UserRole
    from app.core.security import hash_password, create_access_token

    other_user = User(
        id=uuid.uuid4(),
        name="Other Customer",
        email=f"other_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("Pass@123"),
        role=UserRole.CUSTOMER,
        is_active=True
    )
    db.add(other_user)
    db.commit()

    token = create_access_token(user_id=other_user.id, role=other_user.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        f"/api/v1/documents/{uploaded_document.id}/complete",
        headers=headers
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == ErrorCode.DOCUMENT_ACCESS_DENIED
