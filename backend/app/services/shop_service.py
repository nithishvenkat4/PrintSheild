import math
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session
try:
    from geoalchemy2.elements import WKTElement
    from geoalchemy2.shape import to_shape
    from shapely.geometry import Point
except ImportError:
    WKTElement = None
    to_shape = None
    Point = None

from app.models.shop import Shop
from app.models.user import User, UserRole
from app.models.audit_log import AuditAction
from app.core.exceptions import AppException, ErrorCode
from app.services.audit_service import audit_service


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Calculate distance in meters between two coordinates using Haversine formula."""
    r = 6371000.0  # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return int(round(r * c))


def create_point_element(longitude: float, latitude: float, is_sqlite: bool) -> Any:
    """Create appropriate Point representation for PostgreSQL or SQLite."""
    if is_sqlite or WKTElement is None:
        return f"POINT({longitude} {latitude})"
    return WKTElement(f"POINT({longitude} {latitude})", srid=4326)


def extract_coordinates(location: Any) -> tuple[float, float]:
    """Extract (latitude, longitude) from Point or WKT string."""
    if isinstance(location, str):
        # Format: POINT(lon lat)
        cleaned = location.replace("POINT", "").replace("(", "").replace(")", "").strip()
        parts = cleaned.split()
        if len(parts) == 2:
            return float(parts[1]), float(parts[0])
        return 0.0, 0.0
    if to_shape is not None and Point is not None:
        try:
            shape = to_shape(location)
            if isinstance(shape, Point):
                return shape.y, shape.x
        except Exception:
            pass
    return 0.0, 0.0


class ShopService:
    @staticmethod
    def create_shop(
        db: Session,
        owner: User,
        name: str,
        phone: str,
        address: str,
        latitude: float,
        longitude: float,
        ip_address: Optional[str] = None
    ) -> Shop:
        # Check if owner already owns a shop (Phase 1: 1 owner = 1 shop)
        existing = db.query(Shop).filter(Shop.owner_id == owner.id).first()
        if existing:
            raise AppException(
                status_code=409,
                code=ErrorCode.SHOP_NOT_OWNER,
                message="User already owns a registered shop."
            )

        # Validate coordinate bounds
        if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
            raise AppException(
                status_code=400,
                code=ErrorCode.INVALID_LOCATION,
                message="Latitude must be between -90 and 90, longitude between -180 and 180."
            )

        is_sqlite = db.bind.dialect.name == "sqlite" if db.bind else True
        loc_element = create_point_element(longitude, latitude, is_sqlite)

        new_shop = Shop(
            owner_id=owner.id,
            name=name,
            phone=phone,
            address=address,
            location=loc_element,
            qr_token=uuid.uuid4(),
            is_open=True,
            is_verified=False
        )
        db.add(new_shop)
        db.flush()

        audit_service.log_event(
            db=db,
            action=AuditAction.SHOP_CREATED,
            actor_id=owner.id,
            ip_address=ip_address,
            metadata={"shop_id": str(new_shop.id), "shop_name": new_shop.name}
        )
        db.commit()
        db.refresh(new_shop)
        return new_shop

    @staticmethod
    def get_own_shop(db: Session, owner_id: uuid.UUID) -> Shop:
        shop = db.query(Shop).filter(Shop.owner_id == owner_id).first()
        if not shop:
            raise AppException(
                status_code=404,
                code=ErrorCode.SHOP_NOT_FOUND,
                message="No shop registered for this account."
            )
        return shop

    @staticmethod
    def update_own_shop(
        db: Session,
        owner_id: uuid.UUID,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        is_open: Optional[bool] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> Shop:
        shop = db.query(Shop).filter(Shop.owner_id == owner_id).first()
        if not shop:
            raise AppException(
                status_code=404,
                code=ErrorCode.SHOP_NOT_FOUND,
                message="Shop not found."
            )

        if name is not None:
            shop.name = name
        if phone is not None:
            shop.phone = phone
        if address is not None:
            shop.address = address
        if is_open is not None:
            shop.is_open = is_open

        if latitude is not None and longitude is not None:
            if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
                raise AppException(
                    status_code=400,
                    code=ErrorCode.INVALID_LOCATION,
                    message="Coordinates out of valid geographical bounds."
                )
            is_sqlite = db.bind.dialect.name == "sqlite" if db.bind else True
            shop.location = create_point_element(longitude, latitude, is_sqlite)

        db.commit()
        db.refresh(shop)
        return shop

    @staticmethod
    def resolve_qr(
        db: Session,
        qr_token_str: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            qr_token = uuid.UUID(qr_token_str)
        except ValueError:
            raise AppException(
                status_code=404,
                code=ErrorCode.QR_SHOP_NOT_FOUND,
                message="Invalid QR token format."
            )

        shop = db.query(Shop).filter(Shop.qr_token == qr_token).first()
        if not shop:
            raise AppException(
                status_code=404,
                code=ErrorCode.QR_SHOP_NOT_FOUND,
                message="Shop corresponding to this QR code was not found."
            )

        audit_service.log_event(
            db=db,
            action=AuditAction.QR_ACCESSED,
            actor_id=None,
            ip_address=ip_address,
            metadata={"shop_id": str(shop.id), "qr_token": str(qr_token)}
        )
        db.commit()

        return {
            "shop_id": shop.id,
            "name": shop.name,
            "address": shop.address,
            "is_open": shop.is_open
        }

    @staticmethod
    def get_nearby_shops(
        db: Session,
        latitude: float,
        longitude: float,
        radius: int = 5000,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        # Validate constraints (Section 33 & 34)
        if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
            raise AppException(
                status_code=400,
                code=ErrorCode.INVALID_LOCATION,
                message="Latitude must be between -90 and 90, longitude between -180 and 180."
            )
        if not (100 <= radius <= 10000):
            raise AppException(
                status_code=400,
                code=ErrorCode.INVALID_LOCATION,
                message="Radius must be between 100 and 10000 meters."
            )
        if not (1 <= limit <= 50):
            raise AppException(
                status_code=400,
                code=ErrorCode.INVALID_LOCATION,
                message="Limit must be between 1 and 50."
            )

        is_sqlite = db.bind.dialect.name == "sqlite" if db.bind else False

        if not is_sqlite:
            # PostGIS query using ST_DWithin and ST_Distance
            user_point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
            query = (
                select(
                    Shop,
                    func.round(func.ST_Distance(Shop.location, user_point)).label("distance_meters")
                )
                .where(func.ST_DWithin(Shop.location, user_point, radius))
                .order_by("distance_meters")
                .limit(limit)
            )
            results = db.execute(query).all()
            return [
                {
                    "id": row[0].id,
                    "name": row[0].name,
                    "address": row[0].address,
                    "distance_meters": int(row[1]),
                    "is_open": row[0].is_open
                }
                for row in results
            ]
        else:
            # Fallback calculation for SQLite in local tests
            shops = db.query(Shop).all()
            nearby = []
            for shop in shops:
                shop_lat, shop_lon = extract_coordinates(shop.location)
                dist = haversine_distance_meters(latitude, longitude, shop_lat, shop_lon)
                if dist <= radius:
                    nearby.append({
                        "id": shop.id,
                        "name": shop.name,
                        "address": shop.address,
                        "distance_meters": dist,
                        "is_open": shop.is_open
                    })
            nearby.sort(key=lambda x: x["distance_meters"])
            return nearby[:limit]


shop_service = ShopService()
