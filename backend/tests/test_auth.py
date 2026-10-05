import pytest
from app.models.user import UserRole
from app.core.exceptions import ErrorCode


def test_register_customer_success(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Ananya Sharma",
            "email": "ananya@example.com",
            "password": "Password@123",
            "role": "CUSTOMER"
        }
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["user"]["name"] == "Ananya Sharma"
    assert data["user"]["email"] == "ananya@example.com"
    assert data["user"]["role"] == "CUSTOMER"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


def test_register_shop_owner_success(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Shop Owner Bala",
            "email": "bala_print@example.com",
            "password": "Password@123",
            "role": "SHOP_OWNER"
        }
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["user"]["role"] == "SHOP_OWNER"


def test_register_admin_forbidden(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Hacker Admin",
            "email": "hacker@example.com",
            "password": "Password@123",
            "role": "ADMIN"
        }
    )
    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == ErrorCode.AUTH_INSUFFICIENT_ROLE


def test_register_duplicate_email(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "User One",
            "email": "duplicate@example.com",
            "password": "Password@123"
        }
    )
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "User Two",
            "email": "duplicate@example.com",
            "password": "Password@123"
        }
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == ErrorCode.AUTH_INVALID_CREDENTIALS


def test_login_success(client):
    # Register first
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Login User",
            "email": "login_test@example.com",
            "password": "SecretPassword@123"
        }
    )
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "login_test@example.com",
            "password": "SecretPassword@123"
        }
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login_test@example.com"


def test_login_invalid_password(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Test User",
            "email": "wrong_pwd@example.com",
            "password": "CorrectPassword@123"
        }
    )
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrong_pwd@example.com",
            "password": "IncorrectPassword"
        }
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == ErrorCode.AUTH_INVALID_CREDENTIALS


def test_login_nonexistent_user(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "SomePassword"
        }
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == ErrorCode.AUTH_INVALID_CREDENTIALS


def test_get_me_authenticated(client, customer_headers, customer_user):
    response = client.get("/api/v1/auth/me", headers=customer_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(customer_user.id)
    assert data["email"] == customer_user.email


def test_get_me_unauthenticated(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == ErrorCode.AUTH_TOKEN_INVALID
