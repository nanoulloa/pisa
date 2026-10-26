"""Where jobs and their results live: JSON files locally, Supabase Postgres when deployed."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

import httpx
from pydantic import SecretStr

from pisa_contracts import AnalysisResult, Job
from pisa_engine.storage import Storage


class JobStore(Protocol):
    def save(self, job: Job) -> None: ...

    def get(self, job_id: UUID) -> Job | None: ...

    def save_result(self, result: AnalysisResult) -> None: ...

    def get_result(self, job_id: UUID) -> AnalysisResult | None: ...


class StorageJobStore:
    """Jobs as JSON objects in a Storage. For local development and tests."""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def save(self, job: Job) -> None:
        self._storage.put_bytes(_job_key(job.id), job.model_dump_json().encode())

    def get(self, job_id: UUID) -> Job | None:
        key = _job_key(job_id)
        if not self._storage.exists(key):
            return None
        return Job.model_validate_json(self._storage.get_bytes(key))

    def save_result(self, result: AnalysisResult) -> None:
        self._storage.put_bytes(_result_key(result.job.id), result.model_dump_json().encode())

    def get_result(self, job_id: UUID) -> AnalysisResult | None:
        key = _result_key(job_id)
        if not self._storage.exists(key):
            return None
        return AnalysisResult.model_validate_json(self._storage.get_bytes(key))


class SupabaseJobStore:
    """The `jobs` and `results` tables (supabase/migrations), through Supabase's REST API.

    Uses the secret key, which bypasses row level security; the tables have no policies, so
    nothing else can read or write them.
    """

    def __init__(
        self,
        url: str,
        secret_key: SecretStr,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        key = secret_key.get_secret_value()
        headers = {"apikey": key}
        if key.startswith("eyJ"):  # Legacy service_role JWTs also go in Authorization.
            headers["Authorization"] = f"Bearer {key}"
        self._http = httpx.Client(
            base_url=url.rstrip("/") + "/rest/v1/",
            headers=headers,
            timeout=httpx.Timeout(10.0),
            transport=transport,
        )

    def save(self, job: Job) -> None:
        self._upsert("jobs", job.model_dump(mode="json"))

    def get(self, job_id: UUID) -> Job | None:
        rows = self._select("jobs", {"id": f"eq.{job_id}", "select": "*"})
        return Job.model_validate(rows[0]) if rows else None

    def save_result(self, result: AnalysisResult) -> None:
        payload = {"job_id": str(result.job.id), "result": result.model_dump(mode="json")}
        self._upsert("results", payload)

    def get_result(self, job_id: UUID) -> AnalysisResult | None:
        rows = self._select("results", {"job_id": f"eq.{job_id}", "select": "result"})
        return AnalysisResult.model_validate(rows[0]["result"]) if rows else None

    def _upsert(self, table: str, row: dict[str, Any]) -> None:
        response = self._http.post(
            table, json=row, headers={"Prefer": "resolution=merge-duplicates,return=minimal"}
        )
        response.raise_for_status()

    def _select(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        response = self._http.get(table, params=params)
        response.raise_for_status()
        rows: list[dict[str, Any]] = response.json()
        return rows


def _job_key(job_id: UUID) -> str:
    return f"jobs/{job_id}/job.json"


def _result_key(job_id: UUID) -> str:
    return f"jobs/{job_id}/result.json"
