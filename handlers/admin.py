from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from models import ApiKey
from config import ADMIN_USER_ID
from keyboards import get_main_keyboard, get_delete_key_keyboard

router = Router()

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Отмена")]],
    resize_keyboard=True
)

class AddKey(StatesGroup):
    waiting_for_key = State()
class DeleteKey(StatesGroup):
    waiting_for_selection = State()

@router.message(F.text == "add key")
async def add_key_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_USER_ID:
        return
    await message.answer("Пришлите новый API-ключ:", reply_markup=cancel_kb)
    await state.set_state(AddKey.waiting_for_key)

@router.message(AddKey.waiting_for_key, F.text == "Отмена")
async def cancel_add_key(message: Message, state: FSMContext):
    await state.clear()
    kb = get_main_keyboard(message.from_user.id)
    await message.answer("Добавление отменено.", reply_markup=kb)

@router.message(AddKey.waiting_for_key)
async def add_key_process(message: Message, state: FSMContext, session: AsyncSession):
    if message.from_user.id != ADMIN_USER_ID:
        return
    key = message.text.strip()
    if len(key) < 10:
        await message.answer("Ключ слишком короткий. Попробуйте снова или нажмите 'Отмена'.")
        return

    # 🔥 ИСПРАВЛЕНО: безопасная проверка
    result = await session.execute(select(ApiKey).where(ApiKey.key == key))
    existing = result.scalars().first()

    if existing:
        await message.answer("Ключ уже существует.")
    else:
        session.add(ApiKey(key=key, is_active=1))
        await session.commit()
        kb = get_main_keyboard(message.from_user.id)
        await message.answer("Ключ успешно добавлен! ✅", reply_markup=kb)
    await state.clear()

@router.message(F.text == "delete key")
async def delete_key_start(message: Message, state: FSMContext, session: AsyncSession):
    if message.from_user.id != ADMIN_USER_ID:
        return

    # Получаем ВСЕ ключи (активные и заблокированные)
    result = await session.execute(select(ApiKey))
    keys = result.scalars().all()

    if not keys:
        await message.answer("Нет сохранённых API-ключей.", reply_markup=get_main_keyboard(message.from_user.id))
        return

    await message.answer(
        "Выберите ключ для удаления:\n"
        "✅ — активен\n"
        "🔴 — заблокирован (лимит исчерпан)",
        reply_markup=get_delete_key_keyboard(keys)
    )
    await state.set_state(DeleteKey.waiting_for_selection)

@router.callback_query(F.data == "del_cancel")
async def delete_key_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Удаление отменено.", reply_markup=None)
    await callback.answer()

@router.callback_query(F.data.startswith("del_key_"))
async def delete_key_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if callback.from_user.id != ADMIN_USER_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return

    try:
        key_id = int(callback.data.split("_")[-1])
    except ValueError:
        await callback.answer("Неверный ID ключа", show_alert=True)
        return

    # Удаляем ключ
    stmt = delete(ApiKey).where(ApiKey.id == key_id)
    result = await session.execute(stmt)
    await session.commit()

    if result.rowcount > 0:
        await callback.message.edit_text("Ключ успешно удалён! ✅", reply_markup=None)
    else:
        await callback.message.edit_text("Ключ не найден.", reply_markup=None)

    await state.clear()
    await callback.answer()