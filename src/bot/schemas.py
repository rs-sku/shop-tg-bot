from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from src.db.models import DeliveryTypes


class GoodSchema(BaseModel):
    id: int
    name: str
    description: str
    price: Decimal
    photo_file_path: str | None


class CategorieSchema(BaseModel):
    id: int
    name: str
    goods: list[GoodSchema]


class CartGoodSchema(BaseModel):
    id: int
    name: str
    price: Decimal
    quantity: int


class OrderSchema(BaseModel):
    id: int
    number: UUID
    is_approved: bool
    delivery_type: DeliveryTypes
    status: str
    user_id: int
