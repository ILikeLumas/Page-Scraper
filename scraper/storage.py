from __future__ import annotations

from pathlib import Path


def ensure_output_dir(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target
