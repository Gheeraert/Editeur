from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(project_root: Path) -> bool:
    try:
        from dotenv import load_dotenv  # type: ignore
    except ImportError:
        return False

    dotenv_path = project_root / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path, override=False)
    return True


def _fallback_load_env_file(project_root: Path) -> None:
    env_path = project_root / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _parse_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(slots=True)
class AISettings:
    provider: str = "groq"
    base_url: str = "https://api.groq.com/openai/v1"
    api_key: str | None = None
    model: str = "llama-3.3-70b-versatile"
    timeout_seconds: int = 20
    max_blocks: int = 3

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)


@dataclass(slots=True)
class AppSettings:
    project_root: Path
    sources_dir: Path
    exports_dir: Path
    ai: AISettings
    dotenv_loaded: bool


def load_settings() -> AppSettings:
    project_root = Path(__file__).resolve().parents[3]
    dotenv_loaded = _load_dotenv(project_root)
    if not dotenv_loaded:
        _fallback_load_env_file(project_root)

    ai = AISettings(
        provider=os.environ.get("PURH_AI_PROVIDER", "groq"),
        base_url=os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        api_key=os.environ.get("GROQ_API_KEY"),
        model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        timeout_seconds=_parse_int("GROQ_TIMEOUT_SECONDS", 20),
        max_blocks=_parse_int("GROQ_MAX_BLOCKS", 3),
    )

    sources_dir = project_root / "sources"
    exports_dir = project_root / "out"
    exports_dir.mkdir(parents=True, exist_ok=True)

    return AppSettings(
        project_root=project_root,
        sources_dir=sources_dir,
        exports_dir=exports_dir,
        ai=ai,
        dotenv_loaded=dotenv_loaded,
    )
