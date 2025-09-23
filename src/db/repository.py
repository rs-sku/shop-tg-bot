import logging

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.bot.exceptions import UserDoesNotExist
from src.db.models import (
    Cart,
    Category,
    DeliveryTypes,
    Good,
    Order,
    User,
    cart_good_table,
)

logger = logging.getLogger(__name__)


class Repository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all_categories_goods(self) -> list[Category]:
        async with self._session as session:
            res = await session.execute(select(Category).options(joinedload(Category.goods)))
            res = res.unique()
            return res.scalars().all()

    async def create_cart_user(self, chat_id: int) -> None:
        async with self._session as session:
            user = User(chat_id=chat_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            cart = Cart(user_id=user.id)
            session.add(cart)
            await session.commit()

    async def get_user_by_chat_id(self, chat_id: int) -> User | None:
        async with self._session as session:
            stmt = select(User).filter_by(chat_id=chat_id)
            res = await session.execute(stmt)
            res = res.scalar_one_or_none()

            if not res:
                logger.info(f" User with {chat_id=} doesn't exist")
                raise UserDoesNotExist()
            return res

    async def get_cart_by_user_id(self, user_id: int) -> Cart | None:
        async with self._session as session:
            stmt = select(Cart).filter_by(user_id=user_id).options(joinedload(Cart.goods))
            res = await session.execute(stmt)
            res = res.unique()
            return res.scalar_one_or_none()

    async def add_good_in_cart(self, cart_id: int, good_id: int) -> None:
        async with self._session as session:
            async with session.begin():
                stmt = (
                    select(cart_good_table)
                    .where(
                        cart_good_table.c.cart_id == cart_id,
                        cart_good_table.c.good_id == good_id,
                    )
                    .with_for_update()
                )
                res = await session.execute(stmt)
                row = res.first()

                if row:
                    stmt = (
                        update(cart_good_table)
                        .where(
                            cart_good_table.c.cart_id == cart_id,
                            cart_good_table.c.good_id == good_id,
                        )
                        .values(quantity=row.quantity + 1)
                    )
                    log_msg = f"{good_id=} in {cart_id} increased by one"
                else:
                    stmt = insert(cart_good_table).values(cart_id=cart_id, good_id=good_id)
                    log_msg = f"{good_id=} added in cart {cart_id=}"

                await session.execute(stmt)
                await session.commit()
                logger.info(log_msg)

    async def get_good_quantity(self, cart_id: int) -> dict[int, int]:
        async with self._session as session:
            stmt = select(cart_good_table).where(
                cart_good_table.c.cart_id == cart_id,
            )
            res = await session.execute(stmt)
            row = res.all()

            if not row:
                return {}

            return {r.good_id: r.quantity for r in row}

    async def change_good_quantity(self, cart_id: int, good_id: int, new_quantity: int) -> None:
        async with self._session as session:
            try:
                stmt = (
                    update(cart_good_table)
                    .where(
                        cart_good_table.c.cart_id == cart_id,
                        cart_good_table.c.good_id == good_id,
                    )
                    .values(quantity=new_quantity)
                )
                await session.execute(stmt)
                await session.commit()
            except IntegrityError as e:
                await session.rollback()
                await self.delete_good_from_cart(cart_id, good_id)
                logger.info(f"{e}, {good_id=} deleted")

    async def delete_good_from_cart(self, cart_id: int, good_id: int) -> None:
        async with self._session as session:
            stmt = delete(cart_good_table).where(
                cart_good_table.c.cart_id == cart_id,
                cart_good_table.c.good_id == good_id,
            )
            await session.execute(stmt)
            await session.commit()

    async def add_user_contacts(self, user_id: int, full_name: str, phone: str, adress: str) -> None:
        async with self._session as session:
            stmt = update(User).where(User.id == user_id).values(full_name=full_name, phone=phone, adress=adress)
            await session.execute(stmt)
            await session.commit()

    async def create_order(self, user_id: int, delivery_type: DeliveryTypes) -> Order:
        async with self._session as session:
            order = Order(user_id=user_id, delivery_type=delivery_type)
            session.add(order)
            await session.commit()
            await session.refresh(order)
            return order

    async def change_order_approvement(self, order_id: int, new_status: bool) -> None:
        async with self._session as session:
            stmt = update(Order).where(Order.id == order_id).values(is_approved=new_status)
            await session.execute(stmt)
            await session.commit()

    async def show_orders(self) -> list[Order]:
        async with self._session as session:
            res = await session.execute(select(Order))
            return res.scalars().all()

    async def change_order_status(self, order_id: int, new_status: str) -> None:
        async with self._session as session:
            order = await session.get(Order, order_id)
            if not order:
                raise ValueError(f"{order_id=} not found")
            stmt = update(Order).where(Order.id == order_id).values(status=new_status)
            await session.execute(stmt)
            await session.commit()

    async def add_good(self, validated_data: dict) -> None:
        async with self._session as session:
            good = Good(**validated_data)
            session.add(good)
            await session.commit()

    async def update_good(self, good_name: str, values: dict) -> None:
        async with self._session as session:
            stmt = select(Good).where(Good.name == good_name).with_for_update()
            res = await session.execute(stmt)
            if not res.scalar_one_or_none():
                raise ValueError(f"{good_name=} not found")
            stmt = update(Good).where(Good.name == good_name).values(**values)
            await session.execute(stmt)
            await session.commit()

    async def get_category_id_by_name(self, category_name: str) -> int:
        async with self._session as session:
            stmt = select(Category).where(Category.name == category_name)
            res = await session.execute(stmt)
            res = res.scalar_one_or_none()
            if not res:
                return
            return res.id
