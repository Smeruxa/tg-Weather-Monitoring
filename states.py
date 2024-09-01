from aiogram.fsm.state import State, StatesGroup

class NameLocation(StatesGroup):
    rename = State()

class NameAdd(StatesGroup):
    name = State()