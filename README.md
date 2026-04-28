# Telegram Expense Bot (Google Sheets)

Production-ready Telegram bot that records spending into Google Sheets, running on Raspberry Pi 4.

## Features

- Input format: `<type> <name> <price>`
- Records: `Date | Time | Type | Name | Price`
- Commands: `/start`, `/help`, `/today`, `/month`, `/details`, `/breakdown`, `/add`, `/cancel`, `/daily_on`, `/daily_off`, `/daily_now`
- Price validation (`price > 0`)
- Error handling + logging
- Environment-based configuration
- Polling-based bot (works great on Raspberry Pi)

## Project structure

- `app/config.py` - environment loading and validation
- `app/validator.py` - input and price validation
- `app/sheets_service.py` - Google Sheets read/write and totals
- `app/handlers.py` - Telegram commands and message handler
- `app/main.py` - bot runtime (polling or webhook)
- `run.py` - process entrypoint
- `deploy/pi/` - Raspberry Pi systemd service
- `PI_SETUP.md` - Raspberry Pi setup guide

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
   - `details - Show detailed rows for today or a date`
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

## 4) Deploy on Raspberry Pi

**Quick setup:** SSH into your Pi and run:

```bash
cd ~
git clone <your-repo-url>
cd tele_expense
chmod +x setup-pi.sh
./setup-pi.sh
```

The script will prompt for your bot token, Google Sheet ID, and service account JSON, then create `.env` for you.

For detailed steps, see [PI_SETUP.md](PI_SETUP.md).

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
- `B4`: Selected date (dropdown from existing expense dates)
- `B5`: Selected month (dropdown 1-12)
- `B6`: Selected year (dropdown from existing expense years)
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

## 6) Deploy on Oracle Cloud Always Free VM (Polling, no webhook sleep)

This is the recommended free setup if you want the bot running continuously.

### A. Create VM

1. In Oracle Cloud, create a Compute instance (Ubuntu 22.04 or 24.04, Always Free shape).
2. Save your SSH private key and connect:
   - `ssh -i <your_key.pem> ubuntu@<VM_PUBLIC_IP>`

### B. Install runtime and clone repo

Run on the VM:

- `sudo apt update && sudo apt upgrade -y`
- `sudo apt install -y python3 python3-venv python3-pip git`
- `sudo mkdir -p /opt/tele_expense`
- `sudo chown -R ubuntu:ubuntu /opt/tele_expense`
- `git clone https://github.com/jerald-gjw/tele_expense.git /opt/tele_expense`
- `cd /opt/tele_expense`
- `python3 -m venv .venv`
- `source .venv/bin/activate`
- `pip install -r requirements.txt`

### C. Configure environment

Create `/opt/tele_expense/.env`:

- `BOT_MODE=polling`
- `TELEGRAM_BOT_TOKEN=<your_bot_token>`
- `GOOGLE_SHEET_ID=<your_sheet_id>`
- `GOOGLE_SERVICE_ACCOUNT_JSON=<full_json_single_line_or_multiline_value>`
- `GOOGLE_WORKSHEET_NAME=Expenses`
- `TIMEZONE=Asia/Singapore`
- `LOG_LEVEL=INFO`

Notes:
- For polling mode, `WEBHOOK_BASE_URL`, `WEBHOOK_PATH`, `WEBHOOK_SECRET_TOKEN` are not required.
- Keep `.env` private and never commit it.

### D. Run as a systemd service (auto-start on reboot)

1. Copy service file from this repo:
   - `sudo cp /opt/tele_expense/deploy/oracle/tele-expense.service /etc/systemd/system/tele-expense.service`
2. If your VM username is not `ubuntu`, edit:
   - `sudo nano /etc/systemd/system/tele-expense.service`
   - Change `User=ubuntu` to your actual user.
3. Enable and start service:
   - `sudo systemctl daemon-reload`
   - `sudo systemctl enable tele-expense`
   - `sudo systemctl start tele-expense`
4. Check status/logs:
   - `sudo systemctl status tele-expense`
   - `sudo journalctl -u tele-expense -f`

### E. Update bot after new commits

- `cd /opt/tele_expense`
- `git pull`
- `source .venv/bin/activate`
- `pip install -r requirements.txt`
- `sudo systemctl restart tele-expense`