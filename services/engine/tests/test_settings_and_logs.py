from __future__ import annotations

import io
import logging
from pathlib import Path

import pytest

from pisa_engine.api import _job_store, evidence_store_for
from pisa_engine.jobs import StorageJobStore, SupabaseJobStore
from pisa_engine.logs import REDACTED, JsonFormatter
from pisa_engine.render.store import LocalEvidenceStore, SupabaseEvidenceStore
from pisa_engine.settings import Settings

FAKE_KEY = "LLM_000_not-a-real-key"


def test_paid_calls_are_off_by_default() -> None:
    settings = Settings(_env_file=None)
    assert settings.paid_calls_enabled is False
    assert settings.meta_api_key.get_secret_value() == ""


def test_key_comes_only_from_model_api_key_and_never_shows_in_repr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_API_KEY", FAKE_KEY)
    monkeypatch.setenv("PISA_PAID_CALLS_ENABLED", "true")
    settings = Settings(_env_file=None)
    assert settings.meta_api_key.get_secret_value() == FAKE_KEY
    assert settings.paid_calls_enabled is True
    assert FAKE_KEY not in repr(settings)
    assert FAKE_KEY not in settings.model_dump_json()


def test_empty_env_values_fall_back_to_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PISA_SPEND_CAP_USD", "")
    assert Settings(_env_file=None).spend_cap_usd == 5.0


def test_logs_redact_secrets_in_messages_and_tracebacks() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter([FAKE_KEY]))
    logger = logging.getLogger("pisa.test")
    logger.addHandler(handler)
    try:
        logger.warning("calling with %s", FAKE_KEY)
        try:
            raise RuntimeError(f"boom {FAKE_KEY}")
        except RuntimeError:
            logger.exception("failed", extra={"job_id": "job-1"})
    finally:
        logger.removeHandler(handler)

    output = stream.getvalue()
    assert FAKE_KEY not in output
    assert output.count(REDACTED) == 2  # The message and the exception text.
    assert '"job_id": "job-1"' in output


def test_local_store_overrides_a_configured_supabase(tmp_path: Path) -> None:
    auto = Settings(
        _env_file=None,
        SUPABASE_URL="https://project.supabase.co",
        SUPABASE_SECRET_KEY="sb_secret_not-real",  # noqa: S106 (a placeholder, not a key)
        PISA_DATA_DIR=str(tmp_path),
    )
    assert isinstance(_job_store(auto), SupabaseJobStore)
    assert isinstance(evidence_store_for(auto), SupabaseEvidenceStore)
    local = auto.model_copy(update={"store": "local"})
    assert isinstance(_job_store(local), StorageJobStore)
    assert isinstance(evidence_store_for(local), LocalEvidenceStore)
