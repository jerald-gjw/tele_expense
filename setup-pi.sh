#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Telegram Expense Bot - Raspberry Pi Setup ===${NC}\n"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
SERVICE_USER="${SUDO_USER:-$USER}"

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo -e "${YELLOW}Warning: This may not be a Raspberry Pi${NC}"
fi

# Step 1: Update system
echo -e "${YELLOW}[1/7] Updating system packages...${NC}"
sudo apt update && sudo apt upgrade -y > /dev/null 2>&1
echo -e "${GREEN}✓ System updated${NC}\n"

# Step 2: Install dependencies
echo -e "${YELLOW}[2/7] Installing Python and dependencies...${NC}"
sudo apt install -y python3 python3-pip python3-venv git > /dev/null 2>&1
echo -e "${GREEN}✓ Dependencies installed${NC}\n"

# Step 3: Setup project directory
echo -e "${YELLOW}[3/7] Using project directory at $PROJECT_DIR${NC}"
if [ ! -f "$PROJECT_DIR/run.py" ]; then
    echo -e "${RED}setup-pi.sh must be run from inside the cloned repository${NC}"
    exit 1
fi
cd "$PROJECT_DIR"
echo -e "${GREEN}✓ Project directory ready at $PROJECT_DIR${NC}\n"

# Step 4: Create virtual environment
echo -e "${YELLOW}[4/7] Creating Python virtual environment...${NC}"
python3 -m venv .venv > /dev/null 2>&1
source .venv/bin/activate
echo -e "${GREEN}✓ Virtual environment created${NC}\n"

# Step 5: Install Python packages
echo -e "${YELLOW}[5/7] Installing Python dependencies...${NC}"
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✓ Python packages installed${NC}\n"

# Step 6: Configure environment variables
echo -e "${YELLOW}[6/7] Configuring environment variables...${NC}"
if [ -f ".env" ]; then
    echo -e "${YELLOW}.env already exists. Backing up to .env.backup${NC}"
    cp .env .env.backup
fi

read -r -p "Telegram bot token: " TELEGRAM_BOT_TOKEN
read -r -p "Google Sheet ID: " GOOGLE_SHEET_ID
read -r -p "Google service account JSON file path (recommended, blank to paste one-line JSON): " GOOGLE_SERVICE_ACCOUNT_JSON_PATH

mkdir -p credentials
GOOGLE_SERVICE_ACCOUNT_JSON_FILE="$PROJECT_DIR/credentials/google-service-account.json"

if [ -n "$GOOGLE_SERVICE_ACCOUNT_JSON_PATH" ] && [ -f "$GOOGLE_SERVICE_ACCOUNT_JSON_PATH" ]; then
    cp "$GOOGLE_SERVICE_ACCOUNT_JSON_PATH" "$GOOGLE_SERVICE_ACCOUNT_JSON_FILE"
else
    echo -e "${YELLOW}Paste the full Google service account JSON on one line, then press Enter:${NC}"
    read -r GOOGLE_SERVICE_ACCOUNT_JSON
    printf '%s\n' "$GOOGLE_SERVICE_ACCOUNT_JSON" > "$GOOGLE_SERVICE_ACCOUNT_JSON_FILE"
fi

read -r -p "Google worksheet name [Expenses]: " GOOGLE_WORKSHEET_NAME
GOOGLE_WORKSHEET_NAME="${GOOGLE_WORKSHEET_NAME:-Expenses}"
read -r -p "Timezone [Asia/Singapore]: " TIMEZONE
TIMEZONE="${TIMEZONE:-Asia/Singapore}"

cat > .env << EOF
BOT_MODE=polling
TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN
GOOGLE_SHEET_ID=$GOOGLE_SHEET_ID
GOOGLE_SERVICE_ACCOUNT_JSON_FILE=$GOOGLE_SERVICE_ACCOUNT_JSON_FILE
GOOGLE_WORKSHEET_NAME=$GOOGLE_WORKSHEET_NAME
TIMEZONE=$TIMEZONE
LOG_LEVEL=INFO
EOF

chmod 600 .env
chmod 600 "$GOOGLE_SERVICE_ACCOUNT_JSON_FILE"

echo -e "${GREEN}✓ .env file created automatically${NC}"

# Step 7: Setup systemd service
echo -e "${YELLOW}[7/7] Setting up systemd service...${NC}"
cat <<EOF | sudo tee /etc/systemd/system/tele-expense.service > /dev/null
[Unit]
Description=Telegram Expense Bot
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$PROJECT_DIR/.venv/bin/python $PROJECT_DIR/run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable tele-expense > /dev/null 2>&1
echo -e "${GREEN}✓ Service installed and enabled${NC}\n"

# Test run
echo -e "${YELLOW}Testing bot locally (press Ctrl+C to stop)...${NC}"
timeout 10 python run.py || true
echo ""

# Start service
echo -e "${YELLOW}Starting systemd service...${NC}"
sudo systemctl start tele-expense
sleep 2

if sudo systemctl is-active --quiet tele-expense; then
    echo -e "${GREEN}✓ Service started successfully!${NC}\n"
else
    echo -e "${RED}✗ Service failed to start${NC}"
    echo "Check logs with: sudo journalctl -u tele-expense -n 50"
    exit 1
fi

# Final status
echo -e "${GREEN}=== Setup Complete ===${NC}\n"
echo "Service Status:"
sudo systemctl status tele-expense --no-pager

echo ""
echo -e "${GREEN}Useful commands:${NC}"
echo "  View logs:     sudo journalctl -u tele-expense -f"
echo "  Check status:  sudo systemctl status tele-expense"
echo "  Restart:       sudo systemctl restart tele-expense"
echo "  Stop:          sudo systemctl stop tele-expense"
echo "  Edit config:   nano $PROJECT_DIR/.env"
echo ""
echo -e "${GREEN}Your bot should now be running! 🎉${NC}"
