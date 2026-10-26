"""Jobs and their results, stored as JSON. Local disk now; Supabase implements Storage later."""

from __future__ import annotations

from uuid import UUID

from pisa_contracts import AnalysisResult, Job
from pisa_engine.storage import Storage


class JobStore:
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


def _job_key(job_id: UUID) -> str:
    return f"jobs/{job_id}/job.json"


def _result_key(job_id: UUID) -> str:
    return f"jobs/{job_id}/result.json"
