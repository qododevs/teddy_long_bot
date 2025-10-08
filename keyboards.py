# keyboards.py
from datetime import datetime

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
    """Создаёт inline-клавиатуру для выбора ключа на удаление с цветовыми индикаторами."""
    buttons = []
    now = datetime.utcnow()
    for key in keys:
        display = f"{key.key[:6]}...{key.key[-4:]}" if len(key.key) > 10 else key.key

        # Определяем статус
        if key.blocked_until and key.blocked_until > now:
            status_icon = "🔴"  # заблокирован
        else:
            status_icon = "✅"  # активен

        buttons.append([InlineKeyboardButton(text=f"{status_icon} {display}", callback_data=f"del_key_{key.id}")])

    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="del_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)