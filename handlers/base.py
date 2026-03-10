from database import Database, db
from aiogram import Router, types, F, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
import keyboards
import notifications
import utils

router = Router()

async def show_main_menu(message: types.Message, lang, user_id):
    import datetime
    user_data = await db.get_user_settings(user_id)

    if user_data:
        group_name = user_data['group_name'] if user_data['group_name'] else ("Не выбрана" if lang == "ru" else "Not selected")
        date_mode = user_data['date_mode']
        notifications_enabled = bool(user_data['notifications_enabled'])

        date_info = ""
        today = utils.get_yekt_date()

        if date_mode == 'default':
            start_of_week = today - datetime.timedelta(days=today.weekday())
            end_of_next_week = start_of_week + datetime.timedelta(days=13)
            d1 = start_of_week.strftime("%d.%m.%Y")
            d2 = end_of_next_week.strftime("%d.%m.%Y")
            date_info = f"{d1} - {d2}"
        elif date_mode == 'today':
            date_info = f"{today.strftime('%d.%m.%Y')} ({'Сегодня' if lang == 'ru' else 'Today'})"
        elif date_mode == 'tomorrow':
            tomorrow = today + datetime.timedelta(days=1)
            date_info = f"{tomorrow.strftime('%d.%m.%Y')} ({'Завтра' if lang == 'ru' else 'Tomorrow'})"
        elif date_mode == 'yesterday':
            yesterday = today - datetime.timedelta(days=1)
            date_info = f"{yesterday.strftime('%d.%m.%Y')} ({'Вчера' if lang == 'ru' else 'Yesterday'})"
        elif date_mode == 'custom':
            custom_start = user_data['custom_date_start']
            custom_end = user_data['custom_date_end']
            if custom_start and custom_end:
                try:
                    d1 = datetime.datetime.strptime(custom_start, "%Y-%m-%d").strftime("%d.%m.%Y")
                    d2 = datetime.datetime.strptime(custom_end, "%Y-%m-%d").strftime("%d.%m.%Y")
                    date_info = f"{d1} - {d2}"
                except (ValueError, TypeError):
                    date_info = "Custom"
            else:
                date_info = "Custom"
    else:
        group_name = "Не выбрана" if lang == "ru" else "Not selected"
        date_info = "Default"
        notifications_enabled = False

    text_ru = f"Главное меню.\n🎓 Группа: {group_name}\n📆 Дата: {date_info}"
    text_en = f"Main menu.\n🎓 Group: {group_name}\n📆 Date: {date_info}"

    text = text_ru if lang == "ru" else text_en
    await message.answer(text, reply_markup=keyboards.get_main_menu_keyboard(lang, notifications_enabled))


@router.message(Command('start'))
async def send_welcome(message: types.Message, state: FSMContext):
    await state.clear()
    if not await db.user_exists(message.from_user.id):
        await db.ensure_user(message.from_user.id)
        await message.answer("Привет! Я бот расписания УрФУ.\nHello! I am UrFU schedule bot.\n\nПожалуйста, выберите язык / Please select language:", reply_markup=keyboards.get_language_keyboard())
    else:
        user_data = await db.get_user_settings(message.from_user.id)
        lang = user_data['language']
        await show_main_menu(message, lang, message.from_user.id)


@router.message(Command('help'))
async def send_help(message: types.Message, state: FSMContext):
    await state.clear()
    user_data = await db.get_user_settings(message.from_user.id)
    lang = user_data['language'] if user_data else 'ru'

    if lang == 'ru':
        text = (
            "📖 <b>Помощь</b>\n\n"
            "🎓 <b>Выбрать группу</b> — поиск и выбор учебной группы\n"
            "📆 <b>Выбрать дату</b> — период отображения расписания\n"
            "📅 <b>Показать расписание</b> — расписание для выбранной группы\n"
            "🔔 <b>Уведомления</b> — напоминания за 10 минут до пар\n"
            "🌐 <b>Изменить язык</b> — переключение RU/EN\n\n"
            "Команды: /start — главное меню, /help — эта справка"
        )
    else:
        text = (
            "📖 <b>Help</b>\n\n"
            "🎓 <b>Select Group</b> — search and select study group\n"
            "📆 <b>Select Date</b> — schedule display period\n"
            "📌 <b>Show Schedule</b> — schedule for selected group\n"
            "🔔 <b>Notifications</b> — reminders 10 min before classes\n"
            "🌐 <b>Change Language</b> — switch RU/EN\n\n"
            "Commands: /start — main menu, /help — this help"
        )

    await message.answer(text, parse_mode="HTML")


@router.message(F.text.in_({"🌐 Изменить язык", "🌐 Change Language"}), StateFilter('*'))
async def change_language_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await db.ensure_user(message.from_user.id)
    await message.answer("Выберите язык / Select language:", reply_markup=keyboards.get_language_keyboard())

@router.message(F.text.in_({"🔔 Включить уведомления", "🔕 Выключить уведомления", "🔔 Enable Notifications", "🔕 Disable Notifications"}), StateFilter('*'))
async def toggle_notifications(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    await db.ensure_user(message.from_user.id)
    user_data = await db.get_user_settings(message.from_user.id)
    lang = user_data['language']
    group_id = user_data['group_id']

    if not group_id:
        text = "Сначала выберите группу!" if lang == "ru" else "Select group first!"
        await message.answer(text)
        return

    current_status = bool(user_data['notifications_enabled'])
    new_status = not current_status

    await db.set_notification_status(message.from_user.id, new_status)

    if new_status:
        text = "Уведомления включены! Вы будете получать напоминания за 10 минут до начала пар." if lang == "ru" else "Notifications enabled! You will be reminded 10 minutes before classes."
        # Schedule notifications for today immediately
        notifications.cancel_user_notifications(message.from_user.id)
        await notifications.schedule_for_user(bot, message.from_user.id, group_id, lang, db=db)
    else:
        text = "Уведомления выключены." if lang == "ru" else "Notifications disabled."
        # Cancel all pending notifications for this user
        notifications.cancel_user_notifications(message.from_user.id)

    await message.answer(text)
    await show_main_menu(message, lang, message.from_user.id)

@router.callback_query(F.data.startswith('lang_'))
async def process_language_selection(callback_query: types.CallbackQuery):
    lang = callback_query.data.split('_')[1]
    if not await db.user_exists(callback_query.from_user.id):
        await db.ensure_user(callback_query.from_user.id)
    await db.update_language(callback_query.from_user.id, lang)
    await callback_query.answer()
    if callback_query.message:
        await show_main_menu(callback_query.message, lang, callback_query.from_user.id)


@router.message(Command(commands=['test_notif', 'test-notif']))
async def test_notification(message: types.Message, bot: Bot):
    user_data = await db.get_user_settings(message.from_user.id)
    if not user_data:
        await message.answer("Please /start the bot first.")
        return

    lang = user_data['language']
    group_id = user_data['group_id']

    if not group_id:
        text = "Сначала выберите группу!" if lang == "ru" else "Select group first!"
        await message.answer(text)
        return

    from apscheduler.triggers.date import DateTrigger
    import datetime
    import urfu_api
    import utils

    today = utils.get_yekt_date()
    start_of_week = today - datetime.timedelta(days=today.weekday())
    date_start = start_of_week.strftime("%Y-%m-%d")
    end_of_next_week = start_of_week + datetime.timedelta(days=13)
    date_end = end_of_next_week.strftime("%Y-%m-%d")

    schedule_data = await urfu_api.get_schedule(group_id, date_start, date_end)

    if not schedule_data or 'events' not in schedule_data or not schedule_data['events']:
        text = "Нет пар в дефолтном диапазоне (2 недели) для теста." if lang == "ru" else "No classes in the default 2-week range to test."
        await message.answer(text)
        return

    # Find the next upcoming/current event just to have some real data to show
    events = sorted(schedule_data['events'], key=lambda x: (x['date'], x['timeBegin']))
    
    now = datetime.datetime.now(notifications.YEKT)
    next_event = None

    import logging
    for event in events:
        time_hm = event['timeBegin'][:5]
        lesson_start = datetime.datetime.strptime(f"{event['date']} {time_hm}", "%Y-%m-%d %H:%M")
        lesson_start = lesson_start.replace(tzinfo=notifications.YEKT)
        
        # We want an event that hasn't finished yet (or hasn't started yet)
        # To be safe, let's just pick the first event where the start time is strictly in the future
        if lesson_start > now:
            next_event = event
            break
            
    if not next_event:
        text = "Все пары в дефолтном диапазоне уже прошли. Нет будущих пар для теста." if lang == "ru" else "All classes in the default range have passed. No future classes to test."
        await message.answer(text)
        return
    
    now = datetime.datetime.now(notifications.YEKT)
    run_time = now + datetime.timedelta(seconds=10)

    # Need a fake ID to avoid conflicting with real scheduled jobs
    fake_job_id = f"test_notif_{message.from_user.id}_{datetime.datetime.now().timestamp()}"

    notifications.scheduler.add_job(
        notifications.send_lesson_notification,
        trigger=DateTrigger(run_date=run_time),
        args=[bot, message.from_user.id, next_event, lang, None], # Pass None for DB so it doesn't check 'notifications_enabled' setting for tests
        id=fake_job_id,
        replace_existing=True
    )

    text = "Тестовое уведомление придет через 10 секунд! ⏳" if lang == "ru" else "Test notification will arrive in 10 seconds! ⏳"
    await message.answer(text)

