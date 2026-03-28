from __future__ import annotations

import sys
from pathlib import Path


def app_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent


def default_fixture_root() -> Path:
    return app_base_path() / "sample_data" / "fixtures"

