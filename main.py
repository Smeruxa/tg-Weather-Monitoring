from json_functions import save_users, load_users
from get_weather import get_weather
from states import NameLocation, NameAdd
from TOKEN import API_TOKEN
from keyboard import get_keyboard, get_list_keyboard
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ContentType
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

users = load_users()

def extract_values(string):
    return [float(value) for value in string[string.index("[") + 1:-1].split(", ")]

@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = str(message.from_user.id)

    if user_id not in users:
        users[user_id] = {
            "locations": []
        }
        save_users(users)
        await message.answer("Ваш аккаунт был успешно зарегистрирован!")

    await message.answer("Чтобы продолжить, отправьте ваше местоположение.", reply_markup=get_keyboard(user_id))
    
# Стандартный обработчик текста

@dp.message(F.text, StateFilter(None))
async def handle_message(message: types.Message):
    user_id = str(message.from_user.id)

    if user_id not in users:
        await message.answer("Чтобы начать работу с ботом, введите команду \"/start\"!")
        return

    if message.text == "Добавить местоположение":
        await message.answer("Отправьте ваше местоположение.")
    elif message.text == "Перейти к списку местоположений":
        user_id = str(message.from_user.id)

        if not users[user_id]["locations"]:
            await message.answer("У вас нет сохранённых местоположений. Добавьте новое местоположение.", reply_markup=get_keyboard(user_id))
            return

        await message.answer("Выберите одно из следующих местоположений:", reply_markup=get_list_keyboard(user_id))
    elif message.text in ["✔️ Отслеживать", "❌ Перестать отслеживать"]:
        locations = users[user_id]["locations"]
        if locations:
            locations[0]["tracking"] = not locations[0]["tracking"]
            status = "теперь отслеживается" if locations[0]["tracking"] else "больше не отслеживается"
            await message.answer(f"Местоположение \"{locations[0]["name"]}\" {status}.", reply_markup=get_keyboard(user_id))
            save_users(users)
        else:
            await message.answer("У вас нет сохранённых местоположений. Добавьте новое местоположение.", reply_markup=get_keyboard(user_id))
    else:
        await message.answer("Пожалуйста, используйте кнопки", reply_markup=get_keyboard(user_id))

# Работа со списком местоположений

@dp.callback_query(F.data.startswith("EditLocation"))
async def edit_location(call: types.CallbackQuery):
    user_id = str(call.from_user.id)
    index = int(extract_values(call.data)[0])
    location = users[user_id]["locations"][index]

    tracking_text = "❌ Перестать отслеживать" if location["tracking"] else "✔️ Отслеживать"

    inline_keyboard = [
        [InlineKeyboardButton(text=tracking_text, callback_data=f"ToggleTracking[{index}]")],
        [InlineKeyboardButton(text="Изменить название", callback_data=f"EditName[{index}]")],
        [InlineKeyboardButton(text="Удалить", callback_data=f"DeleteLocation[{index}]")],
        [InlineKeyboardButton(text="Назад", callback_data=f"MoveBack")]
    ]
    await call.message.edit_text(f"Что вы хотите сделать с местоположением \"{location["name"]}\"?\nПоследняя температура: {location["last_temp"]}°C", reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_keyboard))

@dp.callback_query(F.data.startswith("MoveBack"))
async def move_back(call: types.CallbackQuery):
    user_id = str(call.from_user.id)
    await call.message.edit_text("Выберите одно из следующих местоположений:", reply_markup=get_list_keyboard(user_id))
    
@dp.callback_query(F.data.startswith("CancelEdit"))
async def cancel_edit(call: types.CallbackQuery):
    user_id = str(call.from_user.id)
    
    await call.message.edit_text("Список местоположений был закрыт.")

@dp.callback_query(F.data.startswith("ToggleTracking"))
async def toggle_tracking(call: types.CallbackQuery):
    user_id = str(call.from_user.id)
    index = int(extract_values(call.data)[0])
    location = users[user_id]["locations"][index]

    location["tracking"] = not location["tracking"]
    status = "теперь отслеживается" if location["tracking"] else "больше не отслеживается"
    await call.message.edit_text(f"Местоположение \"{location["name"]}\" {status}.")
    save_users(users)

@dp.callback_query(F.data.startswith("EditName"))
async def edit_name(call: types.CallbackQuery, state: FSMContext):
    index = int(extract_values(call.data)[0])
    await state.update_data(edit_index=index)
    await call.message.edit_text("Введите новое название для местоположения:")
    await state.set_state(NameLocation.rename)

@dp.message(NameLocation.rename)
async def set_new_name(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    data = await state.get_data()
    index = data["edit_index"]

    users[user_id]["locations"][index]["name"] = message.text
    save_users(users)

    await message.answer(f"Название местоположения успешно изменено на \"{message.text}\".", reply_markup=get_keyboard(user_id))
    await state.clear()

@dp.callback_query(F.data.startswith("DeleteLocation"))
async def delete_location(call: types.CallbackQuery):
    user_id = str(call.from_user.id)
    index = int(extract_values(call.data)[0])
    location_name = users[user_id]["locations"][index]["name"]

    del users[user_id]["locations"][index]
    save_users(users)

    await call.message.edit_text(f"Местоположение \"{location_name}\" успешно удалено.")
    
# Работа со списком местоположений

# Работа с новой локацией

@dp.message(F.content_type == ContentType.LOCATION)
async def handle_new_location(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    lat = message.location.latitude
    lon = message.location.longitude
    temp = await get_weather(lat, lon)

    if temp is not None:
        for location in users[user_id]["locations"]:
            if location["lat"] == lat and location["lon"] == lon:
                await message.answer(f"В этой точке ({lat}, {lon}) уже существует добавленное местоположение под именем \"{location["name"]}\".")
                return
        
        if len(users[user_id]["locations"]) < 5:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Перезаписать существующее", callback_data=f"LocReplace[{lat}, {lon}, {temp}]")],
                [InlineKeyboardButton(text="Добавить новое", callback_data=f"LocAdd[{lat}, {lon}, {temp}]")],
                [InlineKeyboardButton(text="Отменить добавление", callback_data="LocCancel")]
            ])
            await message.answer("Вы хотите добавить новое местоположение или перезаписать существующее?", reply_markup=keyboard)
        else:
            await message.answer("Вы достигли лимита в 5 местоположений. Перезапишите одно из существующих.")
    else:
        await message.answer("Не удалось получить данные о погоде. Попробуйте снова.")

@dp.callback_query(F.data.startswith("LocAdd"))
async def add_addition(call: types.CallbackQuery, state: FSMContext):
    user_id = str(call.from_user.id)
    data = extract_values(call.data)  
    
    await state.set_state(NameAdd.name)
    await state.update_data(user_id=user_id, lat=data[0], lon=data[1], temp=data[2], call=call)
    await call.message.answer("Введите название для вашей новой гео-позиции.")
    
@dp.message(NameAdd.name)
async def name_add(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data["user_id"]

    for location in users[user_id]["locations"]:
        if location["name"] == message.text:
            await message.answer(f"Местоположение с именем \"{message.text}\" уже существует. Пожалуйста, выберите другое имя.")
            return

    users[user_id]["locations"].append({"lat": data["lat"], "lon": data["lon"], "last_temp": data["temp"], "tracking": False, "name": message.text})
    save_users(users)
    
    await data["call"].message.edit_text("Местоположение было добавлено!")
    
    await message.answer(f"Вы успешно добавили новое местоположение \"{message.text}\"!", reply_markup=get_keyboard(user_id))
    await state.clear()

@dp.callback_query(F.data.startswith("LocReplace"))
async def replace_location_prompt(call: types.CallbackQuery, state: FSMContext):
    user_id = str(call.from_user.id)
    
    if len(users[user_id]["locations"]) > 0:
        lat, lon, temp = extract_values(call.data)
        await state.update_data(new_lat=lat, new_lon=lon, new_temp=temp)

        await call.message.edit_text("Выберите местоположение для перезаписи:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=loc["name"], callback_data=f"ConfirmReplace[{index}]")]
            for index, loc in enumerate(users[user_id]["locations"])
        ]))
    else:
        await call.message.answer("У вас нет доступных местоположений для перезаписи!", reply_markup=get_keyboard(user_id))

@dp.callback_query(F.data.startswith("ConfirmReplace"))
async def confirm_replace(call: types.CallbackQuery, state: FSMContext):
    user_id = str(call.from_user.id)
    index = int(extract_values(call.data)[0])
    data = await state.get_data()

    users[user_id]["locations"][index].update({
        "lat": data["new_lat"],
        "lon": data["new_lon"],
        "last_temp": data["new_temp"]
    })
    save_users(users)

    location_name = users[user_id]["locations"][index]["name"]
    await call.message.edit_text(f"Местоположение \"{location_name}\" успешно перезаписано.")
    await state.clear()

@dp.callback_query(F.data == "LocCancel")
async def cancel_addition(call: types.CallbackQuery):
    await call.message.edit_text("Добавление местоположения отменено.")

# Оповещения
async def weather_monitoring():
    while True:
        for user_id, user_data in list(users.items()):
            for location in user_data["locations"]:
                if location["tracking"]:
                    lat = location["lat"]
                    lon = location["lon"]
                    current_temp = await get_weather(lat, lon)
                    if current_temp is not None:
                        last_temp = location["last_temp"]
                        if last_temp is None or abs(current_temp - last_temp) >= 0.5:
                            await bot.send_message(
                                user_id,
                                f"💡 Оповещение!\n"
                                f"Температура изменилась на {current_temp}°C в \"{location["name"]}\"\n"
                                f"Предыдущая температура: {last_temp}°C"
                            )
                            location["last_temp"] = current_temp
                            save_users(users)
        await asyncio.sleep(60)

async def main():
    asyncio.create_task(weather_monitoring())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
