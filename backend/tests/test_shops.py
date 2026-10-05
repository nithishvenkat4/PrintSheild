import uuid
import pytest
from app.core.exceptions import ErrorCode


def test_create_shop_by_shop_owner(client, shop_owner_headers):
    response = client.post(
        "/api/v1/shops",
        headers=shop_owner_headers,
        json={
            "name": "Quick Print Hub",
            "phone": "+919876543211",
            "address": "45 Anna Salai, Chennai",
            "latitude": 13.0604,
            "longitude": 80.2496
        }
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Quick Print Hub"
    assert data["is_open"] is True
    assert data["is_verified"] is False
    assert "qr_token" in data


def test_create_shop_by_customer_forbidden(client, customer_headers):
    response = client.post(
        "/api/v1/shops",
        headers=customer_headers,
        json={
            "name": "Customer's Rogue Shop",
            "phone": "+919876543212",
            "address": "Somewhere",
            "latitude": 13.0,
            "longitude": 80.0
        }
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == ErrorCode.AUTH_INSUFFICIENT_ROLE


def test_create_duplicate_shop_for_owner(client, shop_owner_headers):
    client.post(
        "/api/v1/shops",
        headers=shop_owner_headers,
        json={
            "name": "Shop One",
            "phone": "+919876543213",
            "address": "First Address",
            "latitude": 13.0,
            "longitude": 80.0
        }
    )
    # Attempt second shop
    response = client.post(
        "/api/v1/shops",
        headers=shop_owner_headers,
        json={
            "name": "Shop Two",
            "phone": "+919876543214",
            "address": "Second Address",
            "latitude": 13.1,
            "longitude": 80.1
        }
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == ErrorCode.SHOP_NOT_OWNER


def test_get_my_shop(client, shop_owner_headers, registered_shop):
    response = client.get("/api/v1/shops/me", headers=shop_owner_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(registered_shop.id)
    assert data["name"] == registered_shop.name


def test_get_my_shop_when_none_exists(client, db):
    from app.models.user import User, UserRole
    from app.core.security import hash_password, create_access_token

    new_owner = User(
        id=uuid.uuid4(),
        name="Empty Shop Owner",
        email=f"empty_owner_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("Pass@123"),
        role=UserRole.SHOP_OWNER,
        is_active=True
    )
    db.add(new_owner)
    db.commit()

    token = create_access_token(user_id=new_owner.id, role=new_owner.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/shops/me", headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == ErrorCode.SHOP_NOT_FOUND


def test_update_my_shop(client, shop_owner_headers, registered_shop):
    response = client.patch(
        "/api/v1/shops/me",
        headers=shop_owner_headers,
        json={
            "name": "Updated Shop Name",
            "is_open": False
        }
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Updated Shop Name"
    assert data["is_open"] is False


def test_resolve_qr_public(client, registered_shop):
    response = client.get(f"/api/v1/shops/qr/{registered_shop.qr_token}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["shop_id"] == str(registered_shop.id)
    assert data["name"] == registered_shop.name
    assert data["address"] == registered_shop.address
    assert data["is_open"] is True


def test_resolve_qr_invalid_token(client):
    fake_token = uuid.uuid4()
    response = client.get(f"/api/v1/shops/qr/{fake_token}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == ErrorCode.QR_SHOP_NOT_FOUND


def test_get_nearby_shops(client, registered_shop):
    # registered_shop is at (13.0418, 80.2376)
    response = client.get(
        "/api/v1/shops/nearby",
        params={
            "latitude": 13.0420,
            "longitude": 80.2380,
            "radius": 5000,
            "limit": 10
        }
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["shops"]) >= 1
    assert data["shops"][0]["id"] == str(registered_shop.id)
    assert "distance_meters" in data["shops"][0]


def test_nearby_shops_invalid_coords(client):
    response = client.get(
        "/api/v1/shops/nearby",
        params={
            "latitude": 195.0,  # Invalid
            "longitude": 80.0
        }
    )
    assert response.status_code in (400, 422)
