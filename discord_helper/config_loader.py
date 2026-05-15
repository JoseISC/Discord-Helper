from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

APP_NAME = "discord-helper"
CONFIG_DIR = Path.home() / ".config" / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.env"
LOG_DIR = Path.home() / ".local" / "share" / APP_NAME / "logs"


def ensure_directories() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> None:
    ensure_directories()

    if CONFIG_FILE.exists():
        load_dotenv(CONFIG_FILE)


def save_config(values: dict[str, str]) -> None:
    ensure_directories()

    lines: list[str] = []

    for key, value in values.items():
        lines.append(f"{key}={value}")

    CONFIG_FILE.write_text("\n".join(lines) + "\n")


def get_required_env(key: str) -> str | None:
    return os.getenv(key)
