# keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_USER_ID

def get_main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="Очистить контекст"),
            KeyboardButton(text="Остановить ответ")
        ]
    ]
    if user_id == ADMIN_USER_ID:
        keyboard.append([
            KeyboardButton(text="add key"),
            KeyboardButton(text="delete key")
        ])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
def get_delete_key_keyboard(keys: list) -> InlineKeyboardMarkup:
    """Создаёт inline-клавиатуру со списком ключей для удаления."""
    buttons = []
    for key in keys:
        # Обрезаем ключ для отображения (оставляем начало и конец)
        display = f"{key.key[:6]}...{key.key[-4:]}" if len(key.key) > 10 else key.key
        buttons.append([InlineKeyboardButton(text=display, callback_data=f"del_key_{key.id}")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="del_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)