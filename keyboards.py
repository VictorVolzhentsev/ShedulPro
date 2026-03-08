from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_language_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Русский 🇷🇺", callback_data="lang_ru"),
        InlineKeyboardButton(text="English 🇬🇧", callback_data="lang_en")
    )
    return builder.as_markup()


def get_main_menu_keyboard(language="ru", notifications_enabled=False):
    builder = ReplyKeyboardBuilder()

    btn_schedule = "📌 Показать расписание"
    btn_group = "🎓 Выбрать группу"
    btn_date = "📆 Выбрать дату"
    btn_lang = "🌐 Изменить язык"

    if language == "ru":
        btn_notif = "🔕 Выключить уведомления" if notifications_enabled else "🔔 Включить уведомления"
    else:
        btn_notif = "🔕 Disable Notifications" if notifications_enabled else "🔔 Enable Notifications"

    if language == "en":
        btn_schedule = "📌 Show Schedule"
        btn_group = "🎓 Select Group"
        btn_date = "📆 Select Date"
        btn_lang = "🌐 Change Language"

    builder.row(KeyboardButton(text=btn_lang), KeyboardButton(text=btn_group))
    builder.row(KeyboardButton(text=btn_date), KeyboardButton(text=btn_schedule))
    builder.row(KeyboardButton(text=btn_notif))

    return builder.as_markup(resize_keyboard=True)


def get_date_selection_keyboard(language="ru"):
    builder = InlineKeyboardBuilder()
    if language == "ru":
        builder.row(
            InlineKeyboardButton(text="Вчера", callback_data="date_yesterday"),
            InlineKeyboardButton(text="Сегодня", callback_data="date_today"),
        )
        builder.row(
            InlineKeyboardButton(text="Завтра", callback_data="date_tomorrow"),
            InlineKeyboardButton(text="По умолчанию (2 недели)", callback_data="date_default")
        )
        builder.row(
            InlineKeyboardButton(text="Выбрать диапазон 🗓", callback_data="date_custom")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="Yesterday", callback_data="date_yesterday"),
            InlineKeyboardButton(text="Today", callback_data="date_today"),
        )
        builder.row(
            InlineKeyboardButton(text="Tomorrow", callback_data="date_tomorrow"),
            InlineKeyboardButton(text="Default (2 weeks)", callback_data="date_default")
        )
        builder.row(
            InlineKeyboardButton(text="Select Range 🗓", callback_data="date_custom")
        )
    return builder.as_markup()


def get_paginated_groups_keyboard(groups, page: int = 0, page_size: int = 8, language: str = "ru"):
    builder = InlineKeyboardBuilder()

    start_offset = page * page_size
    end_offset = start_offset + page_size

    for group in groups[start_offset:end_offset]:
        # B4/B6: Only store group_id in callback_data (title fetched from FSM state)
        callback_data = f"sg_{group['id']}"
        builder.row(InlineKeyboardButton(text=f"{group['title']}", callback_data=callback_data))

    nav_buttons = []
    if start_offset > 0:
        prev_text = "⬅️ Назад" if language == "ru" else "⬅️ Back"
        nav_buttons.append(InlineKeyboardButton(text=prev_text, callback_data=f"groups_page_{page-1}"))

    if end_offset < len(groups):
        next_text = "Вперед ➡️" if language == "ru" else "Next ➡️"
        nav_buttons.append(InlineKeyboardButton(text=next_text, callback_data=f"groups_page_{page+1}"))

    if nav_buttons:
        builder.row(*nav_buttons)

    return builder.as_markup()
