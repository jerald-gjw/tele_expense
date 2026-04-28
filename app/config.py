from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_mode: str
    telegram_bot_token: str
    google_sheet_id: str
    google_service_account_json: str | None
    google_service_account_json_file: str | None
    worksheet_name: str
    timezone: str
    port: int
    webhook_base_url: str
    webhook_path: str
    webhook_secret_token: str | None
    log_level: str

    @property
    def tzinfo(self) -> ZoneInfo:
        try:
            return ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")

    @property
    def webhook_url(self) -> str:
        return f"{self.webhook_base_url.rstrip('/')}{self.webhook_path}"

    @property
    def parsed_service_account_info(self) -> dict:
        if self.google_service_account_json_file:
            return json.loads(Path(self.google_service_account_json_file).read_text())
        if self.google_service_account_json:
            return json.loads(self.google_service_account_json)
        raise ValueError("Missing Google service account credentials")


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def load_settings() -> Settings:
    bot_mode = os.getenv("BOT_MODE", "polling").strip().lower() or "polling"
    if bot_mode not in {"webhook", "polling"}:
        raise ValueError("BOT_MODE must be either 'webhook' or 'polling'")

    webhook_base_url = os.getenv("WEBHOOK_BASE_URL", "").strip()
    if bot_mode == "webhook" and not webhook_base_url:
        raise ValueError("WEBHOOK_BASE_URL is required when BOT_MODE=webhook")

    webhook_path = os.getenv("WEBHOOK_PATH", "/webhook").strip() or "/webhook"
    if not webhook_path.startswith("/"):
        webhook_path = f"/{webhook_path}"

    google_service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    google_service_account_json_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_FILE", "").strip()
    if not google_service_account_json and not google_service_account_json_file:
        raise ValueError(
            "Missing Google service account credentials: set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_JSON_FILE"
        )

    return Settings(
        bot_mode=bot_mode,
        telegram_bot_token=_required_env("TELEGRAM_BOT_TOKEN"),
        google_sheet_id=_required_env("GOOGLE_SHEET_ID"),
        google_service_account_json=google_service_account_json or None,
        google_service_account_json_file=google_service_account_json_file or None,
        worksheet_name=os.getenv("GOOGLE_WORKSHEET_NAME", "Expenses"),
        timezone=os.getenv("TIMEZONE", "UTC"),
        port=int(os.getenv("PORT", "10000")),
        webhook_base_url=webhook_base_url,
        webhook_path=webhook_path,
        webhook_secret_token=os.getenv("WEBHOOK_SECRET_TOKEN"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
