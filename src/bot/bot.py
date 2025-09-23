import logging
from enum import Enum
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BotCommand,
    FSInputFile,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from aiogram.types.callback_query import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.exceptions import UserDoesNotExist, WrongContactsInput
from src.bot.service import Service
from src.db.models import DeliveryTypes

logger = logging.getLogger(__name__)


class TextConstants(Enum):
    GREETINGS = "Добро пожаловать в наш магазин!"
    CATEGORIES = "Категории товаров"
    CART = "Корзина"
    GOODS = "Товары"
    ADD_TO_CART = "Добавить в корзину"
    GOOD_ADDED = "Товар успешно добавлен в корзину"
    OPEN_CART = "Посмотреть содержимое корзины"
    CREATE_ORDER = "Оформить заказ"
    CHOOSE_ACTION = "Выберите действие:"
    CALCULATE_CART_COST = "Посчитать общую стоимость"
    DELETE_GOOD = "Удалить из корзины"
    CHANGE_QUANTITY = "Изменить количество"
    REQUEST_QUANTITY = "Введите новое количество товара одним числом"
    QUANTITY_ANSWER = "Количество товара успешно обновлено"
    CONTACTS_REQUEST = "Введите через запятую в таком же порядке: ФИО, телефон начиная с +7, адрес"
    PICKUP = "Забрать самовывозом"
    TO_HOME = "Доставка по указанному адресу"
    CHOOSE_RECEIVING = "Выберите способ получения товара"
    APPROVE = "Да"
    NOT_APPROVE = "Нет"
    RECREATE_ORDER = "Пройдите процесс создания заказа заново"
    ORDER_NUMBER = "Номер вашего заказа: "
    INPUT_TOKEN = "Введите токен администратора"
    GOOD_INPUT_FORMAT = (
        "name:<название товара>,description:<описание товара>,price:<цена товара>,category_name:<название категории>"
    )
    GOOD_UPDATE_INPUT_FROMAT = (
        "name:<новое название товара>,description:<новое описание товара>,price:<новая цена товара>,"
        "category_name:<название категории>,<исходное название товара>"
    )
    STATUS_INPUT_FORMAT = "<id заказа>,<новый статус>"
    NO_ORDERS = "Заказов не найдено"
    INPUT_HINT = "Введите после команды текст в строго следующем формате:\n"
    UPDATE_INPUT_HINT = "\nПервые три поля оптицональны"


class BotCmds(Enum):
    START = "start"
    HELP = "help"
    ADMIN = "admin"

    SHOW_ORDERS = "show_orders"
    CHANGE_ORDER_STATUS = "change_status"
    ADD_GOOD = "add_good"
    EDIT_GOOD = "edit_good"


DELIVERY_TYPES_MAP = {
    DeliveryTypes.PICKUP.value: TextConstants.PICKUP.value,
    DeliveryTypes.TO_HOME.value: TextConstants.TO_HOME.value,
}


class QuantityChange(StatesGroup):
    waiting_for_number = State()


class ContatsRequest(StatesGroup):
    waiting_for_contacts = State()


class ApprovementRequest(StatesGroup):
    waiting_for_approvement = State()


class AdminTokenRequest(StatesGroup):
    waiting_for_token = State()


class ShopBot:
    def __init__(self, dp: Dispatcher, bot_obj: Bot, service: Service, admin_token: str) -> None:
        self._dp = dp
        self._bot = bot_obj
        self._service = service
        self._admin_token = admin_token

    async def _set_commands(self) -> None:
        commands = [
            BotCommand(command=BotCmds.START.value, description="Start bot"),
            BotCommand(command=BotCmds.HELP.value, description="Help"),
            BotCommand(command=BotCmds.ADMIN.value, description="Show admin commans"),
        ]
        await self._bot.set_my_commands(commands)

    async def start(self) -> None:
        await self._set_commands()
        self._start_cmd_handler()
        self._help_cmd_handler()
        self._admin_cmd_handler()
        self._show_admin_cmds()
        self._handle_show_orders_cmd()
        self._handle_change_status_cmd()
        self._handle_add_good_cmd()
        self._handle_edit_good_cmd()
        self._handle_category()
        self._handle_categories_goods()
        self._handle_add_in_cart()
        self._handle_cart()
        self._handle_cart_goods()
        self._handle_delete_good_from_cart()
        self._handle_request_quantity()
        self._handle_change_quantity()
        self._handle_request_contacts()
        self._handle_add_contacts()
        self._handle_order_approvement_request()
        self._handle_order_approvement()
        await self._dp.start_polling(self._bot)

    def _start_cmd_handler(self) -> None:
        @self._dp.message(CommandStart())
        async def handler(msg: Message) -> None:
            chat_id = msg.chat.id
            try:
                await self._service.check_user_existance(chat_id)
            except UserDoesNotExist:
                await self._service.create_cart_user(chat_id)
            keyboard = self._build_main_keyboard()
            await msg.answer(TextConstants.GREETINGS.value, reply_markup=keyboard)

    def _help_cmd_handler(self) -> None:
        @self._dp.message(Command(BotCmds.HELP.value))
        async def handler(msg: Message) -> None:
            await msg.answer(
                text=f"Доступные команды:\n/{BotCmds.START.value}\n/{BotCmds.HELP.value}\n/{BotCmds.ADMIN.value}"
            )

    def _admin_cmd_handler(self) -> None:
        @self._dp.message(Command(BotCmds.ADMIN.value))
        async def handle(msg: Message) -> None:
            await msg.answer(text=TextConstants.INPUT_TOKEN.value)

    def _show_admin_cmds(self) -> None:
        @self._dp.message(F.text == f"{self._admin_token}")
        async def handle(msg: Message) -> None:
            await msg.answer(
                text=(
                    f"Доступные команды:\n/{BotCmds.SHOW_ORDERS.value}\n/{BotCmds.CHANGE_ORDER_STATUS.value}\n"
                    f"/{BotCmds.ADD_GOOD.value}\n/{BotCmds.EDIT_GOOD.value}"
                )
            )

    def _handle_show_orders_cmd(self) -> None:
        @self._dp.message(Command(BotCmds.SHOW_ORDERS.value))
        async def handle(msg: Message) -> None:
            text = await self._service.show_orders()
            if not text:
                text = TextConstants.NO_ORDERS.value
            await msg.answer(text=text)

    def _handle_change_status_cmd(self) -> None:
        @self._dp.message(Command(BotCmds.CHANGE_ORDER_STATUS.value))
        async def hangle(msg: Message, command: CommandObject) -> None:
            if not command.args:
                text = f"{TextConstants.INPUT_HINT.value}{TextConstants.STATUS_INPUT_FORMAT.value}"
            else:
                text = await self._service.change_order_status(command.args)
            await msg.answer(text=text)

    def _handle_add_good_cmd(self) -> None:
        @self._dp.message(Command(BotCmds.ADD_GOOD.value))
        async def handle(msg: Message, command: CommandObject) -> None:
            if not command.args:
                text = f"{TextConstants.INPUT_HINT.value}{TextConstants.GOOD_INPUT_FORMAT.value}"
            else:
                text = await self._service.add_good(command.args)
            await msg.answer(text=text)

    def _handle_edit_good_cmd(self) -> None:
        @self._dp.message(Command(BotCmds.EDIT_GOOD.value))
        async def handle(msg: Message, command: CommandObject) -> None:
            if not command.args:
                text = (
                    f"{TextConstants.INPUT_HINT.value}{TextConstants.GOOD_UPDATE_INPUT_FROMAT.value}"
                    f"{TextConstants.UPDATE_INPUT_HINT.value}"
                )
            else:
                text = await self._service.update_good(command.args)
            await msg.answer(text=text)

    def _build_main_keyboard(self) -> None:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text=TextConstants.CATEGORIES.value),
                    KeyboardButton(text=TextConstants.CART.value),
                ],
            ],
            resize_keyboard=True,
        )
        return keyboard

    def _handle_category(self) -> None:
        @self._dp.message(F.text == TextConstants.CATEGORIES.value)
        async def handle(msg: Message) -> None:
            categories_schemas = await self._service.get_validated_categories_goods()
            builder = InlineKeyboardBuilder()
            for i, category_schema in enumerate(categories_schemas):
                builder.button(text=category_schema.name, callback_data=f"Category:{i}")
            builder.adjust(1)
            await msg.answer(
                f"{TextConstants.CATEGORIES.value}:",
                reply_markup=builder.as_markup(),
            )

    def _handle_categories_goods(self) -> None:
        @self._dp.callback_query(F.data.startswith("Category:"))
        async def handler(callback: CallbackQuery) -> None:
            categories_schemas = await self._service.get_validated_categories_goods()
            ind_x = int(callback.data.split(":")[1])
            for i, good_schema in enumerate(categories_schemas[ind_x].goods):
                good_data = self._service.display_good_base(good_schema)
                text, relative_path = (
                    good_data["text"],
                    good_data["photo_path"],
                )
                builder = InlineKeyboardBuilder()
                builder.button(
                    text=TextConstants.ADD_TO_CART.value,
                    callback_data=f"AddGood:{i}:{ind_x}",
                )
                if relative_path:
                    BASE_DIR = Path(__file__).parent.parent.parent  # Be carefull if reorgonised project
                    photo_path = BASE_DIR / relative_path
                    if photo_path.exists():
                        photo = FSInputFile(photo_path)
                        await callback.message.answer_photo(photo)
                await callback.message.answer(text, reply_markup=builder.as_markup())
            await callback.answer()

    def _handle_add_in_cart(self) -> None:
        @self._dp.callback_query(F.data.startswith("AddGood:"))
        async def handle(callback: CallbackQuery) -> None:
            categories_schemas = await self._service.get_validated_categories_goods()
            good_indx, category_indx = (
                int(callback.data.split(":")[1]),
                int(callback.data.split(":")[2]),
            )
            chat_id = callback.message.chat.id
            good_id = categories_schemas[category_indx].goods[good_indx].id
            text = TextConstants.GOOD_ADDED.value
            try:
                await self._service.add_good_in_cart(chat_id, good_id)
            except UserDoesNotExist as e:
                text = str(e)
            await callback.message.answer(text=text)
            await callback.answer()

    def _handle_cart(self) -> None:
        @self._dp.message(F.text == TextConstants.CART.value)
        async def handle(msg: Message) -> None:
            builder = InlineKeyboardBuilder()
            builder.button(
                text=TextConstants.OPEN_CART.value,
                callback_data=TextConstants.OPEN_CART.value,
            )
            builder.button(
                text=TextConstants.CREATE_ORDER.value,
                callback_data=TextConstants.CREATE_ORDER.value,
            )
            builder.adjust(1)
            await msg.answer(
                text=TextConstants.CHOOSE_ACTION.value,
                reply_markup=builder.as_markup(),
            )

    def _handle_cart_goods(self) -> None:
        @self._dp.callback_query(F.data == TextConstants.OPEN_CART.value)
        async def handle(callback: CallbackQuery) -> None:
            chat_id = callback.message.chat.id
            try:
                cart_goods_schemas = await self._service.get_goods_from_cart(chat_id)
            except UserDoesNotExist as e:
                await callback.message.answer(text=str(e))
                await callback.answer()
            for cart_good_schema in cart_goods_schemas:
                good_id = cart_good_schema.id
                builder = InlineKeyboardBuilder()
                builder.button(
                    text=TextConstants.DELETE_GOOD.value,
                    callback_data=f"Delete:{good_id}",
                )
                builder.button(
                    text=TextConstants.CHANGE_QUANTITY.value,
                    callback_data=f"Quantity:{good_id}",
                )
                text = self._service.display_good_in_cart(cart_good_schema)
                await callback.message.answer(text=text, reply_markup=builder.as_markup())
            total_cost = await self._service.display_total_cost(chat_id)
            await callback.message.answer(text=total_cost)
            await callback.answer()

    def _handle_delete_good_from_cart(self) -> None:
        @self._dp.callback_query(F.data.startswith("Delete:"))
        async def handle(callback: CallbackQuery) -> None:
            chat_id = callback.message.chat.id
            good_id = int(callback.data.split(":")[1])
            text = await self._service.delete_good_from_cart(chat_id, good_id)
            await callback.message.answer(text=text)
            await callback.answer()

    def _handle_request_quantity(self) -> None:
        @self._dp.callback_query(F.data.startswith("Quantity:"))
        async def handle(callback: CallbackQuery, state: FSMContext) -> None:
            good_id = callback.data.split(":")[1]
            await state.update_data(good_id=good_id)
            await callback.message.answer(text=TextConstants.REQUEST_QUANTITY.value)
            await state.set_state(QuantityChange.waiting_for_number)
            await callback.answer()

    def _handle_change_quantity(self) -> None:
        @self._dp.message(QuantityChange.waiting_for_number, F.text.regexp(r"^\d+$"))
        async def handle(msg: Message, state: FSMContext) -> None:
            data = await state.get_data()
            good_id = int(data["good_id"])
            chat_id = msg.chat.id
            new_quantity = int(msg.text)
            await self._service.change_quantity(chat_id, good_id, new_quantity)
            answer = TextConstants.QUANTITY_ANSWER.value
            await msg.answer(text=answer)
            await state.clear()

    def _handle_request_contacts(self) -> None:
        @self._dp.callback_query(F.data == TextConstants.CREATE_ORDER.value)
        async def handle(callback: CallbackQuery, state: FSMContext) -> None:
            await callback.message.answer(text=TextConstants.CONTACTS_REQUEST.value)
            await state.set_state(ContatsRequest.waiting_for_contacts)
            await callback.answer()

    def _handle_add_contacts(self) -> None:
        @self._dp.message(ContatsRequest.waiting_for_contacts)
        async def handle(msg: Message, state: FSMContext) -> None:
            chat_id = msg.chat.id
            contacts = msg.text
            try:
                await self._service.add_user_contacts(chat_id, contacts)
                builder = InlineKeyboardBuilder()
                builder.button(
                    text=TextConstants.PICKUP.value,
                    callback_data=DeliveryTypes.PICKUP.value,
                )
                builder.button(
                    text=TextConstants.TO_HOME.value,
                    callback_data=DeliveryTypes.TO_HOME.value,
                )
                builder.adjust(1)
                await msg.answer(
                    TextConstants.CHOOSE_RECEIVING.value,
                    reply_markup=builder.as_markup(),
                )
            except WrongContactsInput as e:
                await msg.answer(text=str(e))
            finally:
                await state.clear()

    def _handle_order_approvement_request(self) -> None:
        @self._dp.callback_query(F.data.in_([DeliveryTypes.PICKUP.value, DeliveryTypes.TO_HOME.value]))
        async def handle(callback: CallbackQuery, state: FSMContext) -> None:
            delivery_type = callback.data
            chat_id = callback.message.chat.id
            await state.update_data(delivery_type=delivery_type)
            contacts = await self._service.display_user_contacts(chat_id)
            text = (
                contacts
                + f"\n{DELIVERY_TYPES_MAP[delivery_type]}\n{TextConstants.APPROVE.value}/"
                f"{TextConstants.NOT_APPROVE.value}?"
            )
            await callback.message.answer(text=text)
            await state.set_state(ApprovementRequest.waiting_for_approvement)
            await callback.answer()

    def _handle_order_approvement(self) -> None:
        @self._dp.message(
            ApprovementRequest.waiting_for_approvement,
            F.text.in_([TextConstants.APPROVE.value, TextConstants.NOT_APPROVE.value]),
        )
        async def handle(msg: Message, state: FSMContext) -> None:
            if msg.text == TextConstants.NOT_APPROVE.value:
                await msg.answer(TextConstants.RECREATE_ORDER.value)
                await state.clear()
                return
            data = await state.get_data()
            delivery_type = data["delivery_type"]
            chat_id = msg.chat.id
            order_number = await self._service.create_order(chat_id, delivery_type)
            await msg.answer(text=f"{TextConstants.ORDER_NUMBER.value}{order_number}")
            await state.clear()
