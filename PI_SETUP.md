# Raspberry Pi 4 Setup Guide

## Prerequisites

- Raspberry Pi 4 (2GB+ RAM recommended)
- Raspbian OS (latest)
- SSH access or terminal

## Quick Setup (Automated)

Run the automated setup script (recommended):

```bash
cd ~
git clone <your-repo-url>
cd tele_expense
chmod +x setup-pi.sh
./setup-pi.sh
```

The script will:
- ✓ Update system packages
- ✓ Install Python, pip, venv, git
- ✓ Create virtual environment
- ✓ Install Python dependencies
- ✓ Prompt for credentials and create `.env` plus a credentials JSON file automatically
- ✓ Setup systemd service
- ✓ Test and start the bot

**That's it!** After the script completes, your bot will be running as a service.

---

## Manual Installation Steps

If you prefer manual setup, follow these steps:

### 1. SSH into your Pi

```bash
ssh <your_user>@raspberrypi.local
# or: ssh <your_user>@<your_pi_ip>
```

### 2. Update system

```bash
sudo apt update && sudo apt upgrade -y
```

### 3. Install Python and dependencies

```bash
sudo apt install -y python3 python3-pip python3-venv git
```

### 4. Clone/setup project directory

```bash
cd ~
git clone <your-repo-url>
cd tele_expense
```

Or if already cloned:
```bash
cd ~/tele_expense
```

### 5. Create and activate virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 6. Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 7. Configure environment variables

The setup script will prompt for:
- Telegram bot token
- Google Sheet ID
- Google service account JSON file path, or pasted one-line JSON if you do not have a file yet
- Worksheet name and timezone

It will then create `.env` and `credentials/google-service-account.json` automatically.

### 8. Test the bot locally

```bash
source .venv/bin/activate
python run.py
```

Press `Ctrl+C` to stop when ready.

### 9. Setup as system service (optional but recommended)

The setup script already creates and installs the service automatically.

If you want to do it manually, create the service file with:

```bash
sudo tee /etc/systemd/system/tele-expense.service > /dev/null <<'EOF'
[Unit]
Description=Telegram Expense Bot
After=network.target

[Service]
Type=simple
User=<your_user>
WorkingDirectory=/home/<your_user>/tele_expense
EnvironmentFile=/home/<your_user>/tele_expense/.env
ExecStart=/home/<your_user>/tele_expense/.venv/bin/python /home/<your_user>/tele_expense/run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable tele-expense
sudo systemctl start tele-expense
```

Check status:
```bash
sudo systemctl status tele-expense
```

View logs:
```bash
sudo journalctl -u tele-expense -f
```

## Notes

- **Polling vs Webhook**: The Pi currently uses polling mode (`BOT_MODE=polling`), which is simpler for Pi setups as it doesn't require a public IP or domain.
- **Auto-restart**: The systemd service will auto-restart the bot if it crashes or Pi reboots.
- **Performance**: Telegram bot polling is lightweight and works well on Pi 4.

## Troubleshooting

### Bot not starting
```bash
sudo systemctl status tele-expense
sudo journalctl -u tele-expense -n 50
```

### Permission denied when starting service
Make sure `.env` file has correct ownership:
```bash
sudo chown $USER:$USER ~/tele_expense/.env
sudo chmod 600 ~/tele_expense/.env
```

### Google Sheets connection issues
Verify `credentials/google-service-account.json` exists and `GOOGLE_SERVICE_ACCOUNT_JSON_FILE` points to it.

## Updating code
```bash
cd ~/tele_expense
git pull
sudo systemctl restart tele-expense
```
