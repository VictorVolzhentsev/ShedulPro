import datetime
import hashlib
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

import urfu_api
import utils
from database import Database

# Yekaterinburg timezone (UTC+5)
YEKT = datetime.timezone(datetime.timedelta(hours=5))

# Scheduler instance
scheduler = AsyncIOScheduler(timezone=YEKT)


def _build_notification_job_id(user_id: int, lesson: dict) -> str:
    signature = "|".join(
        [
            str(lesson.get("date", "")),
            str(lesson.get("timeBegin", "")),
            str(lesson.get("timeEnd", "")),
            str(lesson.get("title", "")),
            str(lesson.get("auditoryTitle", "")),
            str(lesson.get("teacherName", "")),
        ]
    )
    digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:12]
    return f"notif_{user_id}_{digest}"


async def send_lesson_notification(
    bot: Bot,
    user_id: int,
    lesson: dict,
    lang: str,
    db: Database = None,
    expected_generation: int | None = None
):
    """Sends a notification about a specific lesson, checking subscription status first."""
    try:
        # B3: Check if user still has notifications enabled before sending (skip if db is None, e.g. for test_notif)
        if db is not None:
            user_data = await db.get_user_settings(user_id)
            if not user_data or not user_data['notifications_enabled']:
                return
            current_generation = int(user_data['notification_generation'] or 0)
            if expected_generation is not None and current_generation != expected_generation:
                return

        title = lesson.get('title', '')
        # B1: Safely truncate time to HH:MM format
        time_begin = lesson.get('timeBegin', '')[:5]
        time_end = lesson.get('timeEnd', '')[:5]
        load_type = lesson.get('loadType', '')
        auditory_title = lesson.get('auditoryTitle', '')
        auditory_location = lesson.get('auditoryLocation', '')
        teacher = lesson.get('teacherName', '')
        comment = lesson.get('comment', '')
        teacher_comment = lesson.get('teacherComment', '')
        teacher_link = lesson.get('teacherLink', '')

        # Localized labels
        lesson_date_raw = lesson.get('date', '')
        if lesson_date_raw:
            try:
                parsed_date = datetime.datetime.strptime(lesson_date_raw[:10], "%Y-%m-%d")
                date_str = parsed_date.strftime("%d.%m.%y")
            except ValueError:
                date_str = utils.get_yekt_date().strftime("%d.%m.%y")
        else:
            date_str = utils.get_yekt_date().strftime("%d.%m.%y")

        if lang == 'ru':
            lbl_auditory = "Аудитория"
            lbl_teacher = "Преподаватель"
            lbl_comment = "Комментарий"
            lbl_teacher_comment = "Комм. преподавателя"
            lbl_teacher_link = "Ссылка преподавателя"
            alert_prefix = "🔔 <b>Скоро пара!</b>"
        else:
            lbl_auditory = "Auditory"
            lbl_teacher = "Teacher"
            lbl_comment = "Comment"
            lbl_teacher_comment = "Teacher comment"
            lbl_teacher_link = "Teacher link"
            alert_prefix = "🔔 <b>Class starting soon!</b>"

        # Build notification — title first, then time
        time_str = f"{time_begin} - {time_end}" if time_end else time_begin

        text = f"{alert_prefix}\n\n📅 {date_str}\n"
        text += "<blockquote>"
        text += f"📚 <b>{title}</b>\n"
        text += f"⏰ <b>{time_str}</b>"
        if load_type:
            text += f" | {load_type}"
        text += "\n"

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
            text += f"📍 <b>{lbl_auditory}:</b> {auditory}\n"

        if teacher:
            text += f"👨‍🏫 <b>{lbl_teacher}:</b> {teacher}\n"

        if comment:
            text += f"💬 <b>{lbl_comment}:</b> {comment}\n"

        if teacher_comment:
            text += f"📝 <b>{lbl_teacher_comment}:</b> {teacher_comment}\n"

        if teacher_link:
            text += f"🔗 <a href='{teacher_link}'>{lbl_teacher_link}</a>\n"

        text += "</blockquote>"

        await bot.send_message(user_id, text, parse_mode="HTML", disable_web_page_preview=True)
    except (TelegramForbiddenError, TelegramBadRequest) as e:
        logging.info(f"User {user_id} blocked or chat inaccessible ({e}), disabling notifications.")
        if db is not None:
            await db.set_notification_status(user_id, False)
    except Exception as e:
        logging.error(f"Failed to send notification to {user_id}: {e}")


async def schedule_for_user(
    bot: Bot,
    user_id: int,
    group_id: int,
    lang: str,
    db: Database = None,
    schedule_data: dict = None,
    notification_generation: int | None = None
):
    """Schedules notifications for a single user for today.
    
    Args:
        schedule_data: Optional pre-fetched schedule to avoid duplicate API calls (P1).
        db: Database instance for checking subscription status before sending.
    """
    today_str = utils.get_yekt_date().strftime("%Y-%m-%d")

    # P1: Use pre-fetched schedule if available
    if schedule_data is None:
        schedule_data = await urfu_api.get_schedule(group_id, today_str, today_str)

    if not schedule_data or 'events' not in schedule_data:
        return

    if db is not None and notification_generation is None:
        user_data = await db.get_user_settings(user_id)
        if not user_data or not user_data['notifications_enabled']:
            return
        notification_generation = int(user_data['notification_generation'] or 0)

    # B7: Use timezone-aware datetime
    now = datetime.datetime.now(YEKT)

    for event in schedule_data['events']:
        time_str = event['timeBegin']
        try:
            # B1: Truncate to HH:MM in case API returns HH:MM:SS
            time_hm = time_str[:5]

            # B7: Build timezone-aware datetime
            lesson_start = datetime.datetime.strptime(f"{today_str} {time_hm}", "%Y-%m-%d %H:%M")
            lesson_start = lesson_start.replace(tzinfo=YEKT)

            # Notify 10 minutes before
            notification_time = lesson_start - datetime.timedelta(minutes=10)

            if notification_time > now:
                # Pass db to check subscription status before sending
                args = [bot, user_id, event, lang, db, notification_generation] if db else [bot, user_id, event, lang, None, None]
                scheduler.add_job(
                    send_lesson_notification,
                    trigger=DateTrigger(run_date=notification_time),
                    args=args,
                    id=_build_notification_job_id(user_id, event),
                    replace_existing=True
                )
                logging.info(f"Scheduled notification for user {user_id} at {notification_time}")

        except ValueError as e:
            logging.error(f"Error parsing time for event: {e}")


def cancel_user_notifications(user_id: int):
    """B3: Cancels all pending notifications for a specific user."""
    removed = 0
    for job in scheduler.get_jobs():
        if job.id.startswith(f"notif_{user_id}_"):
            job.remove()
            removed += 1
    if removed:
        logging.info(f"Cancelled {removed} notifications for user {user_id}")



async def update_daily_schedule(bot: Bot, db: Database):
    """Runs daily to update notification timers for all subscribers."""
    logging.info("Starting daily schedule update...")
    users = await db.get_users_with_notifications()

    # P1: Group users by group_id to avoid duplicate API calls
    groups_cache: dict[int, dict] = {}
    count = 0

    for user in users:
        user_id = user['user_id']
        group_id = user['group_id']
        lang = user['language']
        notification_generation = int(user['notification_generation'] or 0)

        # Fetch schedule once per group
        if group_id not in groups_cache:
            today_str = utils.get_yekt_date().strftime("%Y-%m-%d")
            groups_cache[group_id] = await urfu_api.get_schedule(group_id, today_str, today_str)

        cancel_user_notifications(user_id)
        await schedule_for_user(
            bot,
            user_id,
            group_id,
            lang,
            db=db,
            schedule_data=groups_cache[group_id],
            notification_generation=notification_generation
        )
        count += 1

    logging.info(f"Daily schedule update finished. Processed {count} users, {len(groups_cache)} unique groups.")


def start_scheduler(bot: Bot, db: Database):
    """Starts the notification scheduler."""
    if scheduler.running:
        return

    # Daily job: update schedules at 01:00 Yekaterinburg time
    scheduler.add_job(
        update_daily_schedule,
        'cron',
        hour=1,
        minute=0,
        args=[bot, db],
        id="daily_schedule_update",
        replace_existing=True
    )

    # Also run immediately on bot startup (after 5 seconds)
    scheduler.add_job(
        update_daily_schedule,
        'date',
        run_date=datetime.datetime.now(YEKT) + datetime.timedelta(seconds=5),
        args=[bot, db],
        id="startup_schedule_update",
        replace_existing=True
    )

    scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
