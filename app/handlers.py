from __future__ import annotations

import logging
from datetime import datetime, time

from telegram import BotCommand, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.config import Settings
from app.models import ExpenseEntry
from app.sheets_service import SheetsService
from app.validator import InputValidationError, parse_expense_text

LOGGER = logging.getLogger(__name__)
INVALID_MESSAGE = "Invalid format. Use: <type> <name> <price>"
ADD_TYPE, ADD_NAME, ADD_PRICE = range(3)
COMMON_TYPES = [["food", "transport", "shopping"], ["bills", "health", "other"]]
COMMON_NAMES = [["lunch", "dinner", "coffee"], ["mrt", "grab", "snack"]]


def register_handlers(application: Application, settings: Settings, sheets_service: SheetsService) -> None:
    application.bot_data["settings"] = settings
    application.bot_data["sheets_service"] = sheets_service

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(CommandHandler("month", month_command))
    application.add_handler(CommandHandler("breakdown", breakdown_command))
    application.add_handler(CommandHandler("daily_on", daily_on_command))
    application.add_handler(CommandHandler("daily_off", daily_off_command))
    application.add_handler(CommandHandler("daily_now", daily_now_command))
    application.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("add", add_start_command)],
            states={
                ADD_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_type_handler)],
                ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name_handler)],
                ADD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_price_handler)],
            },
            fallbacks=[CommandHandler("cancel", add_cancel_command)],
        )
    )
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, expense_message_handler))
    application.add_error_handler(error_handler)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "I record your spending into Google Sheets.\n"
        "Send expenses as: <type> <name> <price>\n"
        "Use /add for guided entry, /help for examples, /today for today's total, /month for this month's total."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Input format: <type> <name> <price>\n"
        "Examples:\n"
        "food lunch 8.50\n"
        "transport mrt 1.90\n"
        "shopping shirt 35\n\n"
        "Interactive mode:\n"
        "/add - guided expense entry\n"
        "/cancel - cancel interactive entry\n\n"
        "Daily summary:\n"
        "/breakdown daily - daily spending breakdown\n"
        "/breakdown weekly - weekly spending breakdown\n"
        "/breakdown monthly - monthly spending breakdown\n"
        "/daily_on - receive daily 10pm summary\n"
        "/daily_off - stop daily summary\n"
        "/daily_now - send summary now"
    )


async def breakdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sheets_service: SheetsService = context.application.bot_data["sheets_service"]
    settings: Settings = context.application.bot_data["settings"]
    now = datetime.now(settings.tzinfo).date()

    mode = "daily"
    if context.args:
        mode = context.args[0].strip().lower()

    try:
        if mode in {"daily", "day", "today"}:
            total, breakdown = sheets_service.get_daily_breakdown(now)
            title = f"Daily breakdown ({now.strftime('%Y-%m-%d')})"
        elif mode in {"weekly", "week"}:
            total, breakdown = sheets_service.get_weekly_breakdown(now)
            week_start = now.fromordinal(now.toordinal() - now.weekday())
            week_end = week_start.fromordinal(week_start.toordinal() + 6)
            title = f"Weekly breakdown ({week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')})"
        elif mode in {"monthly", "month"}:
            total, breakdown = sheets_service.get_monthly_breakdown(now)
            title = f"Monthly breakdown ({now.strftime('%Y-%m')})"
        else:
            await update.effective_message.reply_text(
                "Usage: /breakdown daily, /breakdown weekly, or /breakdown monthly"
            )
            return
    except Exception:
        LOGGER.exception("Failed to compute breakdown for mode=%s", mode)
        await update.effective_message.reply_text("Could not calculate breakdown right now. Please try again.")
        return

    if total <= 0:
        await update.effective_message.reply_text(f"{title}\nNo spending recorded.")
        return

    lines = [title, f"Total spent: ${total:.2f}", "By type:"]
    for expense_type, amount in breakdown:
        lines.append(f"- {expense_type}: ${amount:.2f}")
    await update.effective_message.reply_text("\n".join(lines))


async def daily_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sheets_service: SheetsService = context.application.bot_data["sheets_service"]
    chat_id = update.effective_chat.id
    try:
        sheets_service.subscribe_daily_summary(chat_id)
        await update.effective_message.reply_text(
            "Daily summary enabled. I will send your spending breakdown every day at 10:00 PM."
        )
    except Exception:
        LOGGER.exception("Failed to enable daily summary")
        await update.effective_message.reply_text("Could not enable daily summary right now. Please try again.")


async def daily_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sheets_service: SheetsService = context.application.bot_data["sheets_service"]
    chat_id = update.effective_chat.id
    try:
        sheets_service.unsubscribe_daily_summary(chat_id)
        await update.effective_message.reply_text("Daily summary disabled.")
    except Exception:
        LOGGER.exception("Failed to disable daily summary")
        await update.effective_message.reply_text("Could not disable daily summary right now. Please try again.")


async def daily_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await _send_daily_summary(context, chat_id)


async def add_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "Let's add an expense.\n"
        "Step 1/3: Choose a type below or type your own (single word).",
        reply_markup=ReplyKeyboardMarkup(COMMON_TYPES, resize_keyboard=True, one_time_keyboard=True),
    )
    return ADD_TYPE


async def add_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    expense_type = (update.effective_message.text or "").strip().lower()
    if not expense_type or " " in expense_type:
        await update.effective_message.reply_text("Type must be a single word. Try again.")
        return ADD_TYPE

    context.user_data["pending_expense_type"] = expense_type
    await update.effective_message.reply_text(
        "Step 2/3: Choose a name below or type your own (multiple words allowed).",
        reply_markup=ReplyKeyboardMarkup(COMMON_NAMES, resize_keyboard=True, one_time_keyboard=True),
    )
    return ADD_NAME


async def add_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.effective_message.text or "").strip().lower()
    if not name:
        await update.effective_message.reply_text("Name cannot be empty. Try again.")
        return ADD_NAME

    context.user_data["pending_expense_name"] = name
    await update.effective_message.reply_text(
        "Step 3/3: Enter price (example: 8.50)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ADD_PRICE


async def add_price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    expense_type = context.user_data.get("pending_expense_type", "")
    name = context.user_data.get("pending_expense_name", "")
    price_text = (update.effective_message.text or "").strip()

    try:
        _, _, price = parse_expense_text(f"{expense_type} {name} {price_text}")
    except InputValidationError:
        await update.effective_message.reply_text("Invalid price. Please enter a valid amount like 8.50")
        return ADD_PRICE

    if await _record_expense(update, context, expense_type, name, price):
        context.user_data.pop("pending_expense_type", None)
        context.user_data.pop("pending_expense_name", None)
        return ConversationHandler.END

    return ADD_PRICE


async def add_cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("pending_expense_type", None)
    context.user_data.pop("pending_expense_name", None)
    await update.effective_message.reply_text(
        "Cancelled interactive entry.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sheets_service: SheetsService = context.application.bot_data["sheets_service"]
    settings: Settings = context.application.bot_data["settings"]
    try:
        now = datetime.now(settings.tzinfo)
        total = sheets_service.get_today_total(now.date())
        await update.effective_message.reply_text(f"Today's total: ${total:.2f}")
    except Exception:
        LOGGER.exception("Failed to calculate /today total")
        await update.effective_message.reply_text("Could not calculate today's total right now.")


async def month_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sheets_service: SheetsService = context.application.bot_data["sheets_service"]
    settings: Settings = context.application.bot_data["settings"]
    try:
        now = datetime.now(settings.tzinfo)
        total = sheets_service.get_month_total(now.date())
        await update.effective_message.reply_text(f"This month's total: ${total:.2f}")
    except Exception:
        LOGGER.exception("Failed to calculate /month total")
        await update.effective_message.reply_text("Could not calculate this month's total right now.")


async def expense_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.effective_message.text or "").strip()
    try:
        expense_type, name, price = parse_expense_text(text)
    except InputValidationError:
        await update.effective_message.reply_text(INVALID_MESSAGE)
        return

    await _record_expense(update, context, expense_type, name, price)


async def _record_expense(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    expense_type: str,
    name: str,
    price: float,
) -> bool:
    sheets_service: SheetsService = context.application.bot_data["sheets_service"]
    settings: Settings = context.application.bot_data["settings"]

    try:
        now = datetime.now(settings.tzinfo)
        entry = ExpenseEntry(
            expense_type=expense_type,
            name=name,
            price=price,
            created_at=now,
        )
        sheets_service.append_expense(entry)
    except Exception:
        LOGGER.exception("Failed writing expense to Google Sheets")
        await update.effective_message.reply_text("Could not record expense right now. Please try again.")
        return False

    await update.effective_message.reply_text(f"Recorded: {expense_type} {name} ${price:.2f}")
    return True


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.exception("Unhandled bot exception", exc_info=context.error)


async def set_bot_commands(application: Application) -> None:
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show usage help"),
        BotCommand("today", "Show today's total"),
        BotCommand("month", "Show this month's total"),
        BotCommand("breakdown", "Show daily/weekly/monthly breakdown"),
        BotCommand("add", "Guided expense entry"),
        BotCommand("cancel", "Cancel guided entry"),
        BotCommand("daily_on", "Enable daily 10pm summary"),
        BotCommand("daily_off", "Disable daily 10pm summary"),
        BotCommand("daily_now", "Send daily summary now"),
    ]
    await application.bot.set_my_commands(commands)
    LOGGER.info("Telegram command menu updated")


def schedule_daily_summary(application: Application, settings: Settings) -> None:
    if application.job_queue is None:
        LOGGER.warning("Job queue not available; daily summary scheduler is disabled")
        return

    for job in application.job_queue.get_jobs_by_name("daily_summary_10pm"):
        job.schedule_removal()

    application.job_queue.run_daily(
        callback=daily_summary_job,
        time=time(hour=22, minute=0, tzinfo=settings.tzinfo),
        name="daily_summary_10pm",
    )
    application.job_queue.run_once(
        callback=bootstrap_commands_job,
        when=1,
        name="bootstrap_commands",
    )
    LOGGER.info("Scheduled daily summary job at 22:00 (%s)", settings.timezone)


async def daily_summary_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    sheets_service: SheetsService = context.application.bot_data["sheets_service"]
    subscribers = sheets_service.get_daily_subscribers()
    for chat_id in subscribers:
        await _send_daily_summary(context, chat_id)


async def bootstrap_commands_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_bot_commands(context.application)


async def _send_daily_summary(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    sheets_service: SheetsService = context.application.bot_data["sheets_service"]
    settings: Settings = context.application.bot_data["settings"]
    today = datetime.now(settings.tzinfo).date()

    total, breakdown = sheets_service.get_daily_breakdown(today)
    if total <= 0:
        text = f"Daily summary ({today.strftime('%Y-%m-%d')}):\nNo spending recorded today."
    else:
        lines = [
            f"Daily summary ({today.strftime('%Y-%m-%d')})",
            f"Total spent: ${total:.2f}",
            "Breakdown by type:",
        ]
        for expense_type, amount in breakdown:
            lines.append(f"- {expense_type}: ${amount:.2f}")
        text = "\n".join(lines)

    try:
        await context.bot.send_message(chat_id=chat_id, text=text)
    except Exception:
        LOGGER.exception("Failed sending daily summary to chat_id=%s", chat_id)
