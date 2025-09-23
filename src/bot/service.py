import logging
from decimal import Decimal
from enum import Enum
from uuid import UUID

from src.bot.exceptions import WrongContactsInput
from src.bot.schemas import (
    CartGoodSchema,
    CategorieSchema,
    GoodSchema,
    OrderSchema,
)
from src.db.models import DeliveryTypes
from src.db.repository import Repository

logger = logging.getLogger(__name__)


class TextConstants(Enum):
    QUANTITY_CHANGED = "Количество товара в корзине успешно изменено"
    GOOD_REMOVED = "Товар успешно удалён из корзины"
    INCORRECT_INPUT = "Неверный формат ввода"
    SUCCESSFUL_UPDATE = "Успешное обновление данных"


class Service:
    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    async def get_validated_categories_goods(self) -> list[CategorieSchema]:
        categories = await self._repository.get_all_categories_goods()
        schemas = []
        for category in categories:
            category_schema = CategorieSchema(
                id=category.id,
                name=category.name,
                goods=[GoodSchema.model_validate(good, from_attributes=True) for good in category.goods],
            )
            schemas.append(category_schema)
        return schemas

    def display_good_base(self, good_schema: GoodSchema) -> dict[str, str]:
        res = f"Название: {good_schema.name}\nОписание: {good_schema.description}\nЦена: {good_schema.price}"
        return {"text": res, "photo_path": good_schema.photo_file_path}

    async def create_cart_user(self, chat_id: int) -> None:
        await self._repository.create_cart_user(chat_id)
        logger.info(f"User with {chat_id=} created")

    async def check_user_existance(self, chat_id: int) -> None:
        await self._repository.get_user_by_chat_id(chat_id)
        logger.info(f"User with {chat_id=} already exists")

    async def add_good_in_cart(self, chat_id: int, good_id: int) -> str | None:
        user = await self._repository.get_user_by_chat_id(chat_id)
        cart = await self._repository.get_cart_by_user_id(user.id)
        await self._repository.add_good_in_cart(cart.id, good_id)

    async def get_goods_from_cart(self, chat_id: int) -> list[CartGoodSchema] | str:
        user = await self._repository.get_user_by_chat_id(chat_id)
        cart = await self._repository.get_cart_by_user_id(user.id)
        quantity = await self._repository.get_good_quantity(cart.id)
        return [
            CartGoodSchema(
                id=good.id,
                name=good.name,
                price=good.price,
                quantity=quantity[good.id],
            )
            for good in cart.goods
        ]

    def display_good_in_cart(self, cart_good_schema: CartGoodSchema) -> str:
        return f"Название: {cart_good_schema.name}\nКоличество: {cart_good_schema.quantity}"

    async def display_total_cost(self, chat_id: int) -> str:
        goods_schemas = await self.get_goods_from_cart(chat_id)
        res = 0
        for good_schema in goods_schemas:
            res += good_schema.price * good_schema.quantity
        return f"Стоимость корзины: {res}"

    async def change_quantity(self, chat_id: int, good_id: int, new_quantity: int) -> str:
        user = await self._repository.get_user_by_chat_id(chat_id)
        cart = await self._repository.get_cart_by_user_id(user.id)
        await self._repository.change_good_quantity(cart.id, good_id, new_quantity)
        return TextConstants.QUANTITY_CHANGED.value

    async def delete_good_from_cart(self, chat_id: int, good_id: int) -> str:
        user = await self._repository.get_user_by_chat_id(chat_id)
        cart = await self._repository.get_cart_by_user_id(user.id)
        await self._repository.delete_good_from_cart(cart.id, good_id)
        return TextConstants.GOOD_REMOVED.value

    async def add_user_contacts(self, chat_id: int, contacts: str) -> str:
        valid_contacts = contacts.split(",")
        if len(valid_contacts) != 3:
            raise WrongContactsInput()
        user = await self._repository.get_user_by_chat_id(chat_id)
        await self._repository.add_user_contacts(user.id, valid_contacts[0], valid_contacts[1], valid_contacts[2])

    async def create_order(self, chat_id: int, delivery_type: DeliveryTypes) -> UUID:
        user = await self._repository.get_user_by_chat_id(chat_id)
        order = await self._repository.create_order(user.id, delivery_type)
        await self._repository.change_order_approvement(order.id, True)
        return order.number

    async def display_user_contacts(self, chat_id: int) -> str:
        user = await self._repository.get_user_by_chat_id(chat_id)
        return f"Ваши контактные данные:\nФИО:{user.full_name}\nТелефон:{user.phone}\nАдрес:{user.adress}"

    async def show_orders(self) -> str:
        order_objects = await self._repository.show_orders()
        res = ""
        for order_obj in order_objects:
            schema = OrderSchema.model_validate(order_obj, from_attributes=True)
            res += (
                f"id: {schema.id}, номер: {schema.number}, способ доставки: {schema.delivery_type.value}, "
                f"статус: {schema.status}, user_id: {schema.user_id}\n\n"
            )
        return res

    async def change_order_status(self, values_str: str) -> str:
        spl = values_str.split(",")
        if len(spl) != 2:
            return TextConstants.INCORRECT_INPUT.value
        try:
            order_id, new_status = int(spl[0]), spl[1]
            await self._repository.change_order_status(order_id, new_status)
            msg = TextConstants.SUCCESSFUL_UPDATE.value
        except Exception:
            msg = TextConstants.INCORRECT_INPUT.value
        return msg

    async def update_good(self, values_str: str) -> str:
        try:
            values = values_str.split(",")
            good_name = values.pop(-1)
            valid_values = self._validate_good_input(values)
            category_name = valid_values.pop("category_name")
            category_id = await self._repository.get_category_id_by_name(category_name)
            valid_values["category_id"] = category_id
            await self._repository.update_good(good_name, valid_values)
            msg = TextConstants.SUCCESSFUL_UPDATE.value
        except Exception as e:
            logger.info(f"{e}")
            msg = TextConstants.INCORRECT_INPUT.value
        return msg

    async def add_good(self, values_str: str) -> str:
        try:
            values = values_str.split(",")
            valid_values = self._validate_good_input(values)
            category_name = valid_values.pop("category_name")
            category_id = await self._repository.get_category_id_by_name(category_name)
            valid_values["category_id"] = category_id
            await self._repository.add_good(valid_values)
            msg = TextConstants.SUCCESSFUL_UPDATE.value
        except Exception as e:
            logger.info(f"{e}")
            msg = TextConstants.INCORRECT_INPUT.value
        return msg

    def _validate_good_input(self, values: list[str]) -> dict:
        valid_values = {}
        for value in values:
            spl = value.split(":")
            key, value = spl[0], spl[1]
            if key == "price":
                value = Decimal(value)
            valid_values[key] = value
        logger.info(f"{valid_values=}")
        return valid_values
