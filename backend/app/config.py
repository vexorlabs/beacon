from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_path: Path = Path.home() / ".beacon" / "traces.db"
    backend_port: int = 7474
    log_level: str = "INFO"

    model_config = {"env_prefix": "BEACON_", "env_file": ".env"}


settings = Settings()
