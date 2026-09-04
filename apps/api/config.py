"""Application configuration loaded from the project's .env file."""

import os
from pathlib import Path

from dotenv import load_dotenv


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")


def get_setting(name: str) -> str | None:
    """Return a configured value, with process environment taking precedence."""

    return os.environ.get(name)
