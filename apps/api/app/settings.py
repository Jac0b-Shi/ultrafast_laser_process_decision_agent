from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _discover_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "project9_ultrafast_laser_process_decision_agent.md").exists():
            return parent
        if (parent / "data" / "raw").exists():
            return parent
    return Path.cwd()


def _configured_path(primary_env: str, legacy_env: str, fallback: Path, marker: str | None = None) -> Path:
    primary = os.getenv(primary_env)
    if primary:
        return Path(primary).resolve()

    legacy = os.getenv(legacy_env)
    if legacy:
        candidate = Path(legacy).resolve()
        if marker is None or (candidate / marker).exists():
            return candidate

    return fallback.resolve()


@dataclass(frozen=True)
class Settings:
    project_root: Path
    data_dir: Path
    experiments_dir: Path
    config_dir: Path
    cors_origins: tuple[str, ...]

    @property
    def raw_data_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def feedback_dir(self) -> Path:
        return self.experiments_dir / "feedback_logs"

    @property
    def feedback_jsonl(self) -> Path:
        return self.feedback_dir / "feedback.jsonl"

    @property
    def sqlite_path(self) -> Path:
        return self.experiments_dir / "laser_agent.sqlite3"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    project_root = Path(os.getenv("PROJECT_ROOT", _discover_project_root())).resolve()
    data_dir = _configured_path("LASER_DATA_DIR", "DATA_DIR", project_root / "data", marker="raw")
    experiments_dir = _configured_path(
        "LASER_EXPERIMENTS_DIR", "EXPERIMENTS_DIR", project_root / "experiments"
    )
    config_dir = _configured_path("LASER_CONFIG_DIR", "CONFIG_DIR", project_root / "configs")
    origins = tuple(
        item.strip()
        for item in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
        if item.strip()
    )
    return Settings(
        project_root=project_root,
        data_dir=data_dir,
        experiments_dir=experiments_dir,
        config_dir=config_dir,
        cors_origins=origins,
    )
