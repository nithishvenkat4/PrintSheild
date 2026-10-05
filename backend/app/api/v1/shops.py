import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Request, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_active_user, require_role, require_shop_owner
from app.models.user import User, UserRole
from app.models.shop import Shop
from app.schemas.shop import (
    ShopCreateRequest,
    ShopCreateResponse,
    ShopUpdateRequest,
    ShopMeResponse,
    ShopDetail,
    ShopQRResponse,
    ShopQRDetail,
    NearbyShopsResponse,
    NearbyShopsData,
    NearbyShopItem
)
from app.services.shop_service import shop_service, extract_coordinates

router = APIRouter(prefix="/shops", tags=["Shops"])


def _shop_to_detail(shop: Shop) -> ShopDetail:
    lat, lon = extract_coordinates(shop.location)
    return ShopDetail(
        id=shop.id,
        name=shop.name,
        phone=shop.phone,
        address=shop.address,
        latitude=lat,
        longitude=lon,
        qr_token=shop.qr_token,
        is_open=shop.is_open,
        is_verified=shop.is_verified
    )


@router.post("", response_model=ShopCreateResponse, status_code=status.HTTP_201_CREATED)
def create_shop(
    request_data: ShopCreateRequest,
    req: Request,
    current_user: User = Depends(require_shop_owner),
    db: Session = Depends(get_db)
):
    client_ip = req.client.host if req.client else None
    shop = shop_service.create_shop(
        db=db,
        owner=current_user,
        name=request_data.name,
        phone=request_data.phone,
        address=request_data.address,
        latitude=request_data.latitude,
        longitude=request_data.longitude,
        ip_address=client_ip
    )
    return ShopCreateResponse(data=_shop_to_detail(shop))


@router.get("/me", response_model=ShopMeResponse, status_code=status.HTTP_200_OK)
def get_my_shop(
    current_user: User = Depends(require_shop_owner),
    db: Session = Depends(get_db)
):
    shop = shop_service.get_own_shop(db, current_user.id)
    return ShopMeResponse(data=_shop_to_detail(shop))


@router.patch("/me", response_model=ShopMeResponse, status_code=status.HTTP_200_OK)
def update_my_shop(
    request_data: ShopUpdateRequest,
    current_user: User = Depends(require_shop_owner),
    db: Session = Depends(get_db)
):
    shop = shop_service.update_own_shop(
        db=db,
        owner_id=current_user.id,
        name=request_data.name,
        phone=request_data.phone,
        address=request_data.address,
        is_open=request_data.is_open,
        latitude=request_data.latitude,
        longitude=request_data.longitude
    )
    return ShopMeResponse(data=_shop_to_detail(shop))


@router.get("/qr/{qr_token}", response_model=ShopQRResponse, status_code=status.HTTP_200_OK)
def resolve_qr(
    qr_token: str,
    req: Request,
    db: Session = Depends(get_db)
):
    client_ip = req.client.host if req.client else None
    res = shop_service.resolve_qr(db, qr_token, client_ip)
    return ShopQRResponse(
        data=ShopQRDetail(
            shop_id=res["shop_id"],
            name=res["name"],
            address=res["address"],
            is_open=res["is_open"]
        )
    )


@router.get("/nearby", response_model=NearbyShopsResponse, status_code=status.HTTP_200_OK)
def get_nearby_shops(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
    radius: int = Query(5000, ge=100, le=10000),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    shops_data = shop_service.get_nearby_shops(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius=radius,
        limit=limit
    )
    items = [
        NearbyShopItem(
            id=s["id"],
            name=s["name"],
            address=s["address"],
            distance_meters=s["distance_meters"],
            is_open=s["is_open"]
        )
        for s in shops_data
    ]
    return NearbyShopsResponse(data=NearbyShopsData(shops=items))
