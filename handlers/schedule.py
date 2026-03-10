from database import db
from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import keyboards
import urfu_api
import utils
import datetime
from collections import defaultdict
import re
from .base import show_main_menu

router = Router()

class Form(StatesGroup):
    waiting_for_date_range = State()

WEEKDAYS_RU = {
    0: "Понедельник", 1: "Вторник", 2: "Среда", 3: "Четверг",
    4: "Пятница", 5: "Суббота", 6: "Воскресенье"
}
WEEKDAYS_EN = {
    0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
    4: "Friday", 5: "Saturday", 6: "Sunday"
}

MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}
MONTHS_EN = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
}

@router.message(F.text.in_({"📆 Выбрать дату", "📆 Select Date"}), StateFilter('*'))
async def select_date_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await db.ensure_user(message.from_user.id)
    user_data = await db.get_user_settings(message.from_user.id)
    lang = user_data['language']
    text = "Выберите период:" if lang == "ru" else "Select period:"
    await message.answer(text, reply_markup=keyboards.get_date_selection_keyboard(lang))

@router.message(F.text.in_({"📌 Показать расписание", "📌 Show Schedule"}), StateFilter('*'))
async def show_schedule(message: types.Message, state: FSMContext):
    await state.clear()
    await db.ensure_user(message.from_user.id)
    user_data = await db.get_user_settings(message.from_user.id)
    lang = user_data['language']
    group_id = user_data['group_id']
    group_name = user_data['group_name']
    date_mode = user_data['date_mode']

    if not group_id:
        text = "Сначала выберите группу!" if lang == "ru" else "Select group first!"
        await message.answer(text)
        return

    today = utils.get_yekt_date()
    date_start = None
    date_end = None

    if date_mode == 'yesterday':
        d = today - datetime.timedelta(days=1)
        date_start = d.strftime("%Y-%m-%d")
        date_end = d.strftime("%Y-%m-%d")
    elif date_mode == 'today':
        date_start = today.strftime("%Y-%m-%d")
        date_end = today.strftime("%Y-%m-%d")
    elif date_mode == 'tomorrow':
        d = today + datetime.timedelta(days=1)
        date_start = d.strftime("%Y-%m-%d")
        date_end = d.strftime("%Y-%m-%d")
    elif date_mode == 'custom':
        date_start = user_data['custom_date_start']
        date_end = user_data['custom_date_end']
        if not date_start or not date_end:
             text = "Диапазон дат не выбран. Выберите дату." if lang == "ru" else "Date range not selected."
             await message.answer(text)
             return
    else: # default
        start_of_week = today - datetime.timedelta(days=today.weekday())
        date_start = start_of_week.strftime("%Y-%m-%d")
        end_of_next_week = start_of_week + datetime.timedelta(days=13)
        date_end = end_of_next_week.strftime("%Y-%m-%d")

    schedule_data = await urfu_api.get_schedule(group_id, date_start, date_end)

    if not schedule_data or 'events' not in schedule_data or not schedule_data['events']:
        text = "Расписание не найдено или отсутствует на эти дни." if lang == "ru" else "Schedule not found or empty."
        await message.answer(text)
        return

    d1_obj = datetime.datetime.strptime(date_start, "%Y-%m-%d")
    d2_obj = datetime.datetime.strptime(date_end, "%Y-%m-%d")

    if lang == "ru":
        m1 = MONTHS_RU[d1_obj.month]
        m2 = MONTHS_RU[d2_obj.month]
        header = f"🎓 <b>Группа {group_name}</b> (с {d1_obj.day} {m1} по {d2_obj.day} {m2})"
    else:
        m1 = MONTHS_EN[d1_obj.month]
        m2 = MONTHS_EN[d2_obj.month]
        header = f"🎓 <b>Group {group_name}</b> (from {m1} {d1_obj.day} to {m2} {d2_obj.day})"

    events = sorted(schedule_data['events'], key=lambda x: (x['date'], x['timeBegin']))

    lbl_auditory = "Аудитория" if lang == "ru" else "Auditory"
    lbl_teacher = "Преподаватель" if lang == "ru" else "Teacher"
    lbl_comment = "Комментарий" if lang == "ru" else "Comment"
    lbl_teacher_comment = "Комм. преподавателя" if lang == "ru" else "Teacher comment"
    lbl_teacher_link = "Ссылка преподавателя" if lang == "ru" else "Teacher link"

    events_by_date = defaultdict(list)
    for event in events:
        date_key = event.get('date')
        if not date_key:
            continue
        events_by_date[date_key].append(event)

    empty_char = "ㅤ"
    separator = f"<s>{empty_char * 18}</s>"

    messages = [header]
    current_msg = header

    for date_key, day_events in events_by_date.items():
        d_obj = datetime.datetime.strptime(date_key, "%Y-%m-%d")
        weekday_idx = d_obj.weekday()
        weekday_name = WEEKDAYS_RU[weekday_idx] if lang == "ru" else WEEKDAYS_EN[weekday_idx]
        date_str = d_obj.strftime("%d.%m.%Y")

        day_text = f"\n\n📅 <b>{date_str} ({weekday_name})</b>\n"
        day_text += "<blockquote>"

        for i, event in enumerate(day_events):
            if i > 0:
                day_text += f"\n{separator}\n"

            day_text += f"{empty_char}\n"

            time_begin = event['timeBegin'][:5]
            time_end = event['timeEnd'][:5]
            time = f"{time_begin} - {time_end}"

            title = event['title']
            type_ = event['loadType']

            day_text += f"📚 <b>{title}</b>\n"
            day_text += f"⏰ <b>{time}</b> | {type_}\n"

            auditory_title = event.get('auditoryTitle')
            auditory_location = event.get('auditoryLocation')

            if auditory_title or auditory_location:
                auditory_parts = []
                if auditory_title:
                    auditory_parts.append(auditory_title)
                if auditory_location:
                    map_link = utils.generate_map_link(auditory_location)
                    import re
                    display_location = re.sub(r'\(.*?\)', '', auditory_location).strip()
                    auditory_parts.append(f"<a href='{map_link}'>{display_location}</a>")
                
                auditory = ", ".join(auditory_parts)
                day_text += f"📍 <b>{lbl_auditory}:</b> {auditory}\n"

            teacher = event.get('teacherName')
            if teacher:
                day_text += f"👨‍🏫 <b>{lbl_teacher}:</b> {teacher}\n"

            comment = event.get('comment')
            if comment:
                 day_text += f"💬 <b>{lbl_comment}:</b> {comment}\n"

            teacher_comment = event.get('teacherComment')
            if teacher_comment:
                 day_text += f"📝 <b>{lbl_teacher_comment}:</b> {teacher_comment}\n"

            teacher_link = event.get('teacherLink')
            if teacher_link:
                 day_text += f"🔗 <a href='{teacher_link}'>{lbl_teacher_link}</a>\n"

            day_text += f"{empty_char}"

        day_text += "</blockquote>"

        if len(current_msg) + len(day_text) > 4000:
            messages.append(current_msg)
            current_msg = day_text
        else:
            current_msg += day_text

    if current_msg and current_msg != messages[-1]:
        messages.append(current_msg)

    for msg in messages[1:]:
        await message.answer(msg, parse_mode="HTML", disable_web_page_preview=True)

@router.callback_query(F.data == 'date_custom')
async def process_custom_date_start(callback_query: types.CallbackQuery, state: FSMContext, bot):
    await db.ensure_user(callback_query.from_user.id)
    user_data = await db.get_user_settings(callback_query.from_user.id)
    lang = user_data['language']
    text = "Введите диапазон дат в формате ДД.ММ.ГГГГ - ДД.ММ.ГГГГ\nНапример: 20.01.2026 - 24.01.2026" if lang == "ru" else "Enter date range in format DD.MM.YYYY - DD.MM.YYYY\nExample: 20.01.2026 - 24.01.2026"
    await state.set_state(Form.waiting_for_date_range)
    await callback_query.answer()
    await bot.send_message(callback_query.from_user.id, text)

@router.message(StateFilter(Form.waiting_for_date_range))
async def process_custom_date_input(message: types.Message, state: FSMContext):
    await db.ensure_user(message.from_user.id)
    user_data = await db.get_user_settings(message.from_user.id)
    lang = user_data['language']
    if not message.text:
        error_text = "Введите диапазон дат текстом." if lang == "ru" else "Please enter the date range as text."
        await message.answer(error_text)
        return

    text_input = message.text.strip()

    pattern = r"(\d{1,2}[./-]\d{1,2}[./-]\d{4})\s*[-–]\s*(\d{1,2}[./-]\d{1,2}[./-]\d{4})"
    match = re.search(pattern, text_input)

    if not match:
        error_text = "Неверный формат. Попробуйте еще раз (ДД.ММ.ГГГГ - ДД.ММ.ГГГГ):" if lang == "ru" else "Invalid format. Try again (DD.MM.YYYY - DD.MM.YYYY):"
        await message.answer(error_text)
        return

    d1_str, d2_str = match.groups()
    try:
        d1_str = d1_str.replace('/', '.').replace('-', '.')
        d2_str = d2_str.replace('/', '.').replace('-', '.')
        d1 = datetime.datetime.strptime(d1_str, "%d.%m.%Y")
        d2 = datetime.datetime.strptime(d2_str, "%d.%m.%Y")
        api_d1 = d1.strftime("%Y-%m-%d")
        api_d2 = d2.strftime("%Y-%m-%d")
        await db.update_custom_date_range(message.from_user.id, api_d1, api_d2)
        success_text = f"Диапазон сохранен: {d1_str} - {d2_str}" if lang == "ru" else f"Range saved: {d1_str} - {d2_str}"
        await state.clear()
        await message.answer(success_text)
        await show_main_menu(message, lang, message.from_user.id)
    except ValueError:
        error_text = "Ошибка в дате. Проверьте корректность." if lang == "ru" else "Date error."
        await message.answer(error_text)

@router.callback_query(F.data.startswith('date_'))
async def process_date_selection(callback_query: types.CallbackQuery, bot):
    mode = callback_query.data.split('_')[1]
    if mode == 'custom':
        return
    await db.ensure_user(callback_query.from_user.id)
    await db.update_date_mode(callback_query.from_user.id, mode)
    user_data = await db.get_user_settings(callback_query.from_user.id)
    lang = user_data['language']
    text = "Режим даты сохранен." if lang == "ru" else "Date mode saved."
    await callback_query.answer()
    await bot.send_message(callback_query.from_user.id, text)
    if callback_query.message:
        await show_main_menu(callback_query.message, lang, callback_query.from_user.id)

