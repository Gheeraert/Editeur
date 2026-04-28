from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


def to_plain_data(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_plain_data(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): to_plain_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_plain_data(item) for item in value]
    if isinstance(value, tuple):
        return [to_plain_data(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def to_json(value: Any, *, indent: int = 2) -> str:
    return json.dumps(to_plain_data(value), ensure_ascii=False, indent=indent, sort_keys=True)


def write_json(path: Path, value: Any, *, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_json(value, indent=indent), encoding="utf-8")
