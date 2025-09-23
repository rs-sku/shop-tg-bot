class UserDoesNotExist(Exception):
    def __init__(
        self, msg: str = "Введите команду /start, чтобы зарегестрироваться"
    ) -> None:
        super().__init__(msg)


class WrongContactsInput(Exception):
    def __init__(
        self, msg: str = "Неправильный формат контактов, повторите процедуру заново"
    ) -> None:
        super().__init__(msg)
