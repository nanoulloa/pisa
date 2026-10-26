"""Engine configuration, read from the environment and the repo-root `.env`."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    """All engine settings. Secrets are `SecretStr`, so they never show up in repr or logs."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    meta_api_key: SecretStr = Field(default=SecretStr(""), validation_alias="MODEL_API_KEY")
    meta_api_base_url: str = Field(
        default="https://api.meta.ai/v1", validation_alias="META_MODEL_API_BASE_URL"
    )
    muse_spark_model: str = Field(default="muse-spark-1.3", validation_alias="MUSE_SPARK_MODEL")
    muse_spark_contributor_model: str = Field(
        default="muse-spark-1.3-contributor", validation_alias="MUSE_SPARK_CONTRIBUTOR_MODEL"
    )
    sam_model: str = Field(default="sam-3.1", validation_alias="SAM_MODEL")

    paid_calls_enabled: bool = Field(default=False, validation_alias="PISA_PAID_CALLS_ENABLED")
    spend_cap_usd: float = Field(default=5.0, ge=0, validation_alias="PISA_SPEND_CAP_USD")
    spend_ledger_path: Path = Field(
        default=REPO_ROOT / ".pisa" / "spend.jsonl", validation_alias="PISA_SPEND_LEDGER_PATH"
    )
    log_level: str = Field(default="INFO", validation_alias="PISA_LOG_LEVEL")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
