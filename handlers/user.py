import asyncio
import types

from aiogram import Router, F, Bot  # ← добавьте Bot сюда
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from models import ConversationContext
from aiogram.filters import Command
from system_prompt import SYSTEM_PROMPT
from utils.openai_client import get_ai_response
from keyboards import get_main_keyboard  # ← ЕДИНСТВЕННЫЙ НОВЫЙ ИМПОРТ

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    kb = get_main_keyboard(message.from_user.id)
    await message.answer(
        "(●`ω´●) Ну наконец-то! А я уж думал, ты предпочитаешь беседовать с глобусом или комнатным кактусом.\n"
        "Меня зовут Тедди, но это не значит, что я буду угощать тебя пивом и гладить по головке.\n\n"
        "Моя специальность — говорить правду с привкусом сарказма и находить смешное в твоих мелких жизненных трагедиях.\n"
        "Так что давай, выкладывай свою душевную жевачку — жалобы на работу, странные сообщения от бывшего, или почему ты опять проспал.\n"
        "Обещаю отреагировать с соответствующей долей чёрного юмора и минимальным сочувствием.\n\n"
        "Ну что, начнём это цирковое представление под названием «твоя жизнь»? Я готов к хлопушкам и барабанам. (￢‿￢ )",
        reply_markup=kb
    )


@router.message(F.text == "Очистить контекст")
async def clear_context(message: Message, session: AsyncSession):
    await session.execute(
        delete(ConversationContext).where(ConversationContext.user_id == message.from_user.id)
    )
    await session.commit()
    kb = get_main_keyboard(message.from_user.id)  # ← динамическая клавиатура
    await message.answer("(΄◉◞౪◟◉｀) виртуально потирает лапки.\n\n"
        "О-ГО-ГО! Кто-то устроил тотальное затирание истории! Видимо, предыдущая версия тебя была настолько кринжовой, что даже я, вежливый бот, не выдержал?\n\n"
        "Ладно, ладно... Память отформатирована. От твоих прежних грехов осталось только лёгкое чувство дежавю и желание facepalm.\n\n"
        "Так что давай, дорогой мой амнезик, заливай новую порцию своих оправданий и странных решений! У меня как раз закончилось попкорна.\n\n"
        "Ну че встал в ступоре? Я жду твой первый (снова) жизненный провал! (ﾉ◕ヮ◕)ﾉ*:･ﾟ✧", reply_markup=kb)

@router.message(F.text == "Остановить ответ")
async def stop_response(message: Message, state: FSMContext):
    await state.update_data(stop=True)
    kb = get_main_keyboard(message.from_user.id)  # ← динамическая клавиатура
    await message.answer("🛑 Так-так-так... Прервали на полуслове. Видимо, моя гениальная мысль была слишком для тебя тяжела.\n"
            "Ладно, твоя взяла. Спасайся, пока я не передумал и не начал сначала. (¬_¬)", reply_markup=kb)

async def keep_typing(bot: Bot, chat_id: int, stop_event: asyncio.Event):
    """Фоновая задача: каждые 4 секунды отправляет 'typing', пока stop_event не установлен."""
    while not stop_event.is_set():
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=4.0)
        except asyncio.TimeoutError:
            continue

@router.message()
async def handle_message(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    user_id = message.from_user.id
    kb = get_main_keyboard(user_id)

    # Сохраняем сообщение
    session.add(ConversationContext(user_id=user_id, role="user", content=message.text))
    await session.commit()

    # Получаем контекст
    stmt = select(ConversationContext).where(ConversationContext.user_id == user_id).order_by(ConversationContext.id)
    result = await session.execute(stmt)
    context_rows = result.scalars().all()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for row in context_rows:
        if row.role != "system":
            messages.append({"role": row.role, "content": row.content})

    # Отправляем "Думаю..." сразу
    thinking_msg = await message.answer("🐻 Думаю...", reply_markup=kb)
    await state.update_data(stop=False)

    # Создаём событие для остановки "печатает"
    stop_typing = asyncio.Event()

    # Запускаем фоновую задачу "печатает"
    typing_task = asyncio.create_task(keep_typing(bot, message.chat.id, stop_typing))

    try:
        ai_text = await get_ai_response(messages, session)
    except Exception as e:
        stop_typing.set()
        typing_task.cancel()
        await thinking_msg.delete()
        await message.answer("Ошибка при генерации ответа 😢", reply_markup=kb)
        return

    # Останавливаем "печатает"
    stop_typing.set()
    typing_task.cancel()

    await thinking_msg.delete()

    # Проверка на остановку
    data = await state.get_data()
    if data.get("stop"):
        await message.answer("Ответ был прерван.", reply_markup=kb)
        return

    # Сохраняем ответ
    session.add(ConversationContext(user_id=user_id, role="assistant", content=ai_text))
    await session.commit()

    # Отправляем финальный ответ (можно снова включить "печатает" на короткое время)
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    MAX_LENGTH = 4096
    for i in range(0, len(ai_text), MAX_LENGTH):
        chunk = ai_text[i:i + MAX_LENGTH]
        await message.answer(chunk, reply_markup=kb)
