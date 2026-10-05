import os
import sys
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole
from app.models.shop import Shop
from app.models.document import Document
from app.core.security import hash_password, create_access_token

# Test in-memory SQLite database
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def customer_user(db):
    user = User(
        id=uuid.uuid4(),
        name="Ramesh Kumar",
        email=f"customer_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("Customer@123"),
        role=UserRole.CUSTOMER,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def customer_token(customer_user):
    return create_access_token(user_id=customer_user.id, role=customer_user.role.value)


@pytest.fixture
def customer_headers(customer_token):
    return {"Authorization": f"Bearer {customer_token}"}


@pytest.fixture
def shop_owner_user(db):
    user = User(
        id=uuid.uuid4(),
        name="Suresh Shop Owner",
        email=f"shop_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("Shop@123"),
        role=UserRole.SHOP_OWNER,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def shop_owner_token(shop_owner_user):
    return create_access_token(user_id=shop_owner_user.id, role=shop_owner_user.role.value)


@pytest.fixture
def shop_owner_headers(shop_owner_token):
    return {"Authorization": f"Bearer {shop_owner_token}"}


@pytest.fixture
def admin_user(db):
    user = User(
        id=uuid.uuid4(),
        name="Admin Boss",
        email=f"admin_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("Admin@123"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user):
    return create_access_token(user_id=admin_user.id, role=admin_user.role.value)


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def registered_shop(db, shop_owner_user):
    shop = Shop(
        id=uuid.uuid4(),
        owner_id=shop_owner_user.id,
        name="Sri Lakshmi Xerox & Print Center",
        phone="+919876543210",
        address="12 Gandhi Road, T Nagar, Chennai",
        location="POINT(80.2376 13.0418)",
        qr_token=uuid.uuid4(),
        is_open=True,
        is_verified=True
    )
    db.add(shop)
    db.commit()
    db.refresh(shop)
    return shop


@pytest.fixture
def uploaded_document(db, customer_user):
    doc = Document(
        id=uuid.uuid4(),
        owner_id=customer_user.id,
        original_filename="aadhaar_card.pdf",
        storage_key=f"jobs/{uuid.uuid4()}/test_aadhaar.pdf",
        mime_type="application/pdf",
        file_size=154200,
        checksum_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=60)
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc
