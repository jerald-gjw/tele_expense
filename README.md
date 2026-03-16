# Telegram Expense Bot (Google Sheets)

Production-ready Telegram bot that records spending into Google Sheets.

## Features

- Input format: `<type> <name> <price>`
- Records: `Date | Time | Type | Name | Price`
- Commands: `/start`, `/help`, `/today`, `/month`, `/breakdown`, `/add`, `/cancel`, `/daily_on`, `/daily_off`, `/daily_now`
- Price validation (`price > 0`)
- Error handling + logging
- Environment-based configuration
- Webhook-based deployment for Render (24/7)

## Project structure

- `app/config.py` - environment loading and validation
- `app/validator.py` - input and price validation
- `app/sheets_service.py` - Google Sheets read/write and totals
- `app/handlers.py` - Telegram commands and message handler
- `app/main.py` - webhook runtime
- `run.py` - process entrypoint

## 1) Create Telegram bot (BotFather)

1. Open Telegram and message **@BotFather**.
2. Send `/newbot`.
3. Set bot name and unique username.
4. Copy the bot token and set it as `TELEGRAM_BOT_TOKEN`.

Optional:
- Use `/setdescription` to describe your bot.
- Use `/setcommands` and set:
  - `start - Start the bot`
  - `help - Show usage examples`
  - `today - Show today's total spending`
  - `month - Show this month's total spending`
   - `breakdown - Show daily/weekly/monthly breakdown`
   - `add - Guided expense entry`
   - `cancel - Cancel guided entry`
   - `daily_on - Enable daily 10pm summary`
   - `daily_off - Disable daily 10pm summary`
   - `daily_now - Send summary immediately`

## 2) Connect Google Sheets API

1. Go to Google Cloud Console.
2. Create/select a project.
3. Enable APIs:
   - Google Sheets API
   - Google Drive API
4. Create a **Service Account**.
5. Create a **JSON key** and download it.
6. Open your Google Sheet, copy its ID from URL:
   - `https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit`
7. Share the sheet with the service account email (`client_email` in JSON) as **Editor**.
8. Put full JSON content into `GOOGLE_SERVICE_ACCOUNT_JSON`.
9. Set `GOOGLE_SHEET_ID`.

### Example Google Sheet format

Create worksheet named `Expenses` with header row:

| Date | Time | Type | Name | Price |
|------|------|------|------|-------|
| 2026-03-16 | 13:14:55 | food | lunch | 8.50 |

The bot will auto-write this header if missing.

## 3) Local run

1. Create virtual environment and install dependencies:
   - `python -m venv .venv`
   - `./.venv/Scripts/activate`
   - `pip install -r requirements.txt`
2. Create `.env` from `.env.example` and fill real values.
3. Export env vars (or use VS Code env integration).
4. Run:
   - `python run.py`

## 4) Deploy on Render (Webhook, 24/7)

1. Push this repository to GitHub.
2. In Render, create **New + > Web Service**.
3. Connect your GitHub repo.
4. Build command: `pip install -r requirements.txt`
5. Start command: `python run.py`
6. Add environment variables in Render:
   - `TELEGRAM_BOT_TOKEN`
   - `GOOGLE_SHEET_ID`
   - `GOOGLE_SERVICE_ACCOUNT_JSON`
   - `GOOGLE_WORKSHEET_NAME=Expenses`
   - `TIMEZONE=Asia/Singapore` (or your timezone)
   - `WEBHOOK_BASE_URL=https://<your-service>.onrender.com`
   - `WEBHOOK_PATH=/webhook`
   - `WEBHOOK_SECRET_TOKEN=<long-random-string>` (recommended)
   - `LOG_LEVEL=INFO`
7. Deploy. The bot starts webhook server and automatically registers webhook URL.

## 5) Bot behavior

### Valid input

Message format:

`<type> <name> <price>`

Examples:
- `food lunch 8.50`
- `transport mrt 1.90`
- `shopping shirt 35`

Reply:

`Recorded: <type> <name> $<price>`

### Interactive input

- Send `/add`
- Bot shows quick type buttons (`food`, `transport`, `shopping`, `bills`, `health`, `other`) and also accepts custom type
- Bot then shows quick name buttons (`lunch`, `dinner`, `coffee`, `mrt`, `grab`, `snack`) and also accepts custom name
- Then asks for price
- Use `/cancel` anytime to stop

### Invalid input

Reply:

`Invalid format. Use: <type> <name> <price>`

### Breakdown command

- `/breakdown daily` - shows today's spending breakdown by type
- `/breakdown weekly` - shows this week's spending breakdown by type
- `/breakdown monthly` - shows current month's spending breakdown by type

The bot also auto-registers these commands to Telegram, so typing `/` shows the full command list.

## Notes

- This implementation expects exactly 3 fields in a message.
- `/today` and `/month` totals are computed from current sheet rows.
- Date/time is stored using the timezone from `TIMEZONE`.

## Daily 10PM summary

- Send `/daily_on` once to subscribe this chat.
- Every day at `10:00 PM` (`TIMEZONE` in `.env`), bot sends:
   - total spent for the day
   - breakdown by spending type
- Send `/daily_off` to unsubscribe.
- Send `/daily_now` to test summary immediately.

Subscription data is saved in `Subscriptions` worksheet so it survives restarts.

## Analysis tab

The bot auto-creates a second worksheet named `Analysis` with configurable tracking metrics.

Configuration cells:
- `B4`: Selected date (for exact daily total, e.g. 16/03/2025)
- `B5`: Selected month (1-12)
- `B6`: Selected year (e.g. 2026)
- `B7`: Optional type filter (e.g. `food`)

Included analytics:
- Total on selected date
- Total in selected month
- Total in selected year
- Total on selected date + type filter
- Average daily spend in selected month
- Monthly breakdown by type
- Month-by-month totals for selected year
- Recent 10 expenses table