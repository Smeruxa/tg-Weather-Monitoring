from json_functions import save_users, load_users
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

def get_keyboard(user_id):
    users = load_users()
    buttons = []

    if user_id in users:
        locations = users[user_id]["locations"]
        if len(locations) == 0:
            buttons = [[KeyboardButton(text="Добавить местоположение")]]
        elif len(locations) == 1:
            tracking_text = "❌ Перестать отслеживать" if locations[0]["tracking"] else "✔️ Отслеживать"
            buttons = [
                [KeyboardButton(text=tracking_text)],
                [KeyboardButton(text="Добавить местоположение")]
            ]
        else:
            buttons = [
                [KeyboardButton(text="Перейти к списку местоположений")],
                [KeyboardButton(text="Добавить местоположение")]
            ]

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )
    
def get_list_keyboard(user_id):
    users = load_users()
    inline_keyboard = [
        [InlineKeyboardButton(text=loc["name"], callback_data=f"EditLocation[{idx}]")]
        for idx, loc in enumerate(users[user_id]["locations"])
    ]
    inline_keyboard.append([InlineKeyboardButton(text="Отмена", callback_data=f"CancelEdit")])
    
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)