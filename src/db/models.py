import enum
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
)
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class DeliveryTypes(enum.Enum):
    PICKUP = "PICKUP"
    TO_HOME = "TO_HOME"


class Base(DeclarativeBase, AsyncAttrs):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class User(Base):
    __tablename__ = "users"

    chat_id: Mapped[int] = mapped_column(Integer, unique=True)
    full_name: Mapped[str] = mapped_column(String(128), nullable=True)
    phone: Mapped[str] = mapped_column(String(128), nullable=True, unique=True)
    adress: Mapped[str] = mapped_column(String(256), nullable=True)
    cart = relationship("Cart", back_populates="user")
    orders = relationship("Order", back_populates="user")


class Category(Base):
    __tablename__ = "categories"
    name: Mapped[str] = mapped_column(String(128), unique=True)
    goods = relationship("Good", back_populates="category")


cart_good_table = Table(
    "cart_good",
    Base.metadata,
    Column("cart_id", Integer, ForeignKey("carts.id"), primary_key=True),
    Column("good_id", Integer, ForeignKey("goods.id"), primary_key=True),
    Column("quantity", Integer, default=1),
    CheckConstraint("quantity > 0", name="check_quantity_positive"),
)


class Good(Base):
    __tablename__ = "goods"
    name: Mapped[str] = mapped_column(String(128), unique=True)  # unique to simplify admin management
    description: Mapped[str] = mapped_column(String(256))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    photo_file_path: Mapped[str] = mapped_column(String(128), nullable=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", back_populates="goods")
    carts = relationship("Cart", secondary=cart_good_table, back_populates="goods")


class Cart(Base):
    __tablename__ = "carts"
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="cart")
    goods = relationship("Good", secondary=cart_good_table, back_populates="carts")


class Order(Base):
    __tablename__ = "orders"
    number: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), default=uuid4)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_type: Mapped[DeliveryTypes] = mapped_column(Enum(DeliveryTypes))
    status: Mapped[str] = mapped_column(String(256), default="Created")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="orders")
