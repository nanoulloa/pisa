"""Engine configuration, read from the environment and the repo-root `.env`."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_HERE = Path(__file__).resolve()
# services/engine/src/pisa_engine/settings.py -> repo root. Deployed images have no repo around
# the package, so fall back to the package folder.
REPO_ROOT = _HERE.parents[4] if len(_HERE.parents) > 4 else _HERE.parent


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

    # Where jobs, uploads and results live on this machine.
    data_dir: Path = Field(default=REPO_ROOT / ".pisa" / "data", validation_alias="PISA_DATA_DIR")
    # "fake" tracks the synthetic ball by color for free; "sam" calls SAM 3.1.
    segmenter: Literal["fake", "sam"] = Field(default="fake", validation_alias="PISA_SEGMENTER")
    # "fake" treats the whole clip as one fall of `default_phrase`; "muse_spark" watches it.
    planner: Literal["fake", "muse_spark"] = Field(default="fake", validation_alias="PISA_PLANNER")
    # "none" leaves the wording to the clients' templates; "muse_spark" writes it.
    explainer: Literal["none", "muse_spark"] = Field(
        default="none", validation_alias="PISA_EXPLAINER"
    )
    # Concept phrase for the offline planner.
    default_phrase: str = Field(default="ball", validation_alias="PISA_DEFAULT_PHRASE")
    max_upload_bytes: int = Field(
        default=50_000_000, gt=0, validation_alias="PISA_MAX_UPLOAD_BYTES"
    )
    # Comma-separated origins allowed to call the API from a browser.
    web_origins: str = Field(default="http://localhost:3000", validation_alias="PISA_WEB_ORIGINS")
    # Analyses running at once; more wait their turn.
    max_concurrent_jobs: int = Field(default=2, gt=0, validation_alias="PISA_MAX_CONCURRENT_JOBS")
    # New jobs per client IP per hour.
    jobs_per_hour: int = Field(default=20, gt=0, validation_alias="PISA_JOBS_PER_HOUR")
    # New jobs per hour from everyone together: the backstop no address rotation can get around.
    jobs_per_hour_total: int = Field(default=500, gt=0, validation_alias="PISA_JOBS_PER_HOUR_TOTAL")
    # When set, POST /jobs requires "Authorization: Bearer <token>" (the web server holds it).
    engine_token: SecretStr = Field(default=SecretStr(""), validation_alias="PISA_ENGINE_TOKEN")
    # Behind one trusted proxy (Modal), the client address is the last X-Forwarded-For entry.
    trust_proxy: bool = Field(default=False, validation_alias="PISA_TRUST_PROXY")

    # "auto" keeps jobs, results and evidence in Supabase when it is configured; "local" keeps
    # them on disk even then (tests, and local runs that must not touch production).
    store: Literal["auto", "local"] = Field(default="auto", validation_alias="PISA_STORE")
    # With both set, jobs and results live in Supabase Postgres instead of local files.
    supabase_url: str = Field(default="", validation_alias="SUPABASE_URL")
    supabase_secret_key: SecretStr = Field(
        default=SecretStr(""), validation_alias="SUPABASE_SECRET_KEY"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
