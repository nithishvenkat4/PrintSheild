import uuid
from typing import List, Optional
from pydantic import BaseModel, Field


class ShopCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    phone: str = Field(..., min_length=7, max_length=20)
    address: str = Field(..., min_length=5)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class ShopUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    phone: Optional[str] = Field(None, min_length=7, max_length=20)
    address: Optional[str] = Field(None, min_length=5)
    is_open: Optional[bool] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)


class ShopDetail(BaseModel):
    id: uuid.UUID
    name: str
    phone: str
    address: str
    latitude: float
    longitude: float
    qr_token: uuid.UUID
    is_open: bool
    is_verified: bool

    model_config = {"from_attributes": True}


class ShopCreateResponse(BaseModel):
    data: ShopDetail


class ShopMeResponse(BaseModel):
    data: ShopDetail


class ShopQRDetail(BaseModel):
    shop_id: uuid.UUID
    name: str
    address: str
    is_open: bool


class ShopQRResponse(BaseModel):
    data: ShopQRDetail


class NearbyShopItem(BaseModel):
    id: uuid.UUID
    name: str
    address: str
    distance_meters: int
    is_open: bool


class NearbyShopsData(BaseModel):
    shops: List[NearbyShopItem]


class NearbyShopsResponse(BaseModel):
    data: NearbyShopsData
