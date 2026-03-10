from database import db
from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import keyboards
import urfu_api
from .base import show_main_menu

router = Router()

class Form(StatesGroup):
    waiting_for_group_search = State()

@router.message(F.text.in_({"🎓 Выбрать группу", "🎓 Select Group"}), StateFilter('*'))
async def select_group_start(message: types.Message, state: FSMContext):
    await state.clear()
    await db.ensure_user(message.from_user.id)
    user_data = await db.get_user_settings(message.from_user.id)
    lang = user_data['language']
    text = "Введите название группы (или часть) для поиска:" if lang == "ru" else "Enter group name (or part) to search:"
    await state.set_state(Form.waiting_for_group_search)
    await message.answer(text)

@router.message(StateFilter(Form.waiting_for_group_search))
async def process_group_search(message: types.Message, state: FSMContext):
    await db.ensure_user(message.from_user.id)
    if not message.text:
        user_data = await db.get_user_settings(message.from_user.id)
        lang = user_data['language']
        text = "Введите текст для поиска группы." if lang == "ru" else "Please enter text to search for a group."
        await message.answer(text)
        return

    groups = await urfu_api.search_group(message.text)
    user_data = await db.get_user_settings(message.from_user.id)
    lang = user_data['language']

    if not groups:
        text = "Группы не найдены. Попробуйте еще раз:" if lang == "ru" else "Groups not found. Try again:"
        await message.answer(text)
        return

    if len(groups) == 1:
        group = groups[0]
        await db.update_group(message.from_user.id, group['id'], group['title'])
        text = f"Группа {group['title']} выбрана и сохранена." if lang == "ru" else f"Group {group['title']} selected and saved."
        await state.clear()
        await message.answer(text)
        await show_main_menu(message, lang, message.from_user.id)
    else:
        await state.update_data(found_groups=groups)
        text = "Найдены следующие группы:" if lang == "ru" else "Found groups:"
        await message.answer(text, reply_markup=keyboards.get_paginated_groups_keyboard(groups, page=0, language=lang))

@router.callback_query(F.data.startswith('groups_page_'))
async def process_groups_pagination(callback_query: types.CallbackQuery, state: FSMContext):
    page = int(callback_query.data.split('_')[2])
    data = await state.get_data()
    groups = data.get('found_groups')

    if not groups:
        await callback_query.answer("Данные устарели, повторите поиск.", show_alert=True)
        return

    user_data = await db.get_user_settings(callback_query.from_user.id)
    lang = user_data['language']

    await callback_query.message.edit_reply_markup(
        reply_markup=keyboards.get_paginated_groups_keyboard(groups, page=page, language=lang)
    )
    await callback_query.answer()

@router.callback_query(F.data.startswith('sg_'))
async def process_group_selection(callback_query: types.CallbackQuery, state: FSMContext, bot):
    group_id = int(callback_query.data.split('_')[1])

    # Find group title from stored search results
    data = await state.get_data()
    groups = data.get('found_groups', [])
    group_title = None
    for g in groups:
        if g['id'] == group_id:
            group_title = g['title']
            break

    if not group_title:
        # Fallback: FSM state expired, ask user to search again
        user_data = await db.get_user_settings(callback_query.from_user.id)
        lang = user_data['language']
        text = "Данные устарели, повторите поиск группы." if lang == "ru" else "Data expired, please search again."
        await callback_query.answer(text, show_alert=True)
        return

    await db.update_group(callback_query.from_user.id, group_id, group_title)

    user_data = await db.get_user_settings(callback_query.from_user.id)
    lang = user_data['language']

    text = f"Группа {group_title} выбрана." if lang == "ru" else f"Group {group_title} selected."

    await state.clear()
    await callback_query.answer()
    await bot.send_message(callback_query.from_user.id, text)
    if callback_query.message:
        await show_main_menu(callback_query.message, lang, callback_query.from_user.id)
