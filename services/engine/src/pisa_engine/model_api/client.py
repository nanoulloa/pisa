"""HTTP client for Meta Model API (https://dev.meta.ai/docs).

Every request passes two gates before anything leaves the machine: the data
policy (no contributor-tier model for user videos) and the spend guard (kill
switch and budget). The API key is held as a `SecretStr` and only ever placed in
the Authorization header.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from pydantic import SecretStr

from pisa_contracts import CostEntry, DataPolicy, Stage
from pisa_engine.model_api import costs
from pisa_engine.model_api.policy import ensure_model_allowed
from pisa_engine.model_api.pricing import UnknownPriceError, token_cost_usd
from pisa_engine.model_api.spend import Reservation, SpendGuard

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(30.0, read=300.0)
# Uploaded files never expire unless asked. Jobs delete theirs as soon as they are done; this
# expiry (the shortest the Files API allows) is the backstop if a deletion fails.
FILE_EXPIRY_S = 3600
# Failures that prove the request never reached the API, so nothing can have been billed.
_NEVER_SENT = (httpx.ConnectError, httpx.ConnectTimeout)


class ModelApiError(RuntimeError):
    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"Meta Model API returned HTTP {status_code}: {body[:500]}")
        self.status_code = status_code


class MetaModelApiClient:
    def __init__(
        self,
        *,
        api_key: SecretStr,
        base_url: str,
        guard: SpendGuard,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._guard = guard
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/", timeout=DEFAULT_TIMEOUT, transport=transport
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def upload_file(self, path: Path, *, purpose: str = "user_data") -> str:
        """POST /files. Returns the file id to reference as `file_id`. Prefer `uploaded()`."""
        self._guard.ensure_enabled()
        # Nested form fields in the bracket notation of the OpenAI SDK, which this API mirrors.
        form = {
            "purpose": purpose,
            "expires_after[anchor]": "created_at",
            "expires_after[seconds]": str(FILE_EXPIRY_S),
        }
        with path.open("rb") as media:
            response = await self._http.post(
                "files",
                headers=self._auth_headers(),
                data=form,
                files={"file": (path.name, media, "video/mp4")},
            )
        payload = self._json_or_raise(response)
        file_id = payload.get("id")
        if not isinstance(file_id, str):
            raise ModelApiError(response.status_code, "upload response has no file id")
        if payload.get("expires_at") is None:
            logger.warning("Uploaded file has no expiry; it is deleted after use instead")
        return file_id

    async def delete_file(self, file_id: str) -> None:
        """DELETE /files/{id}. Free, so it runs even when paid calls are switched off."""
        response = await self._http.delete(f"files/{file_id}", headers=self._auth_headers())
        if response.status_code != 404:  # Already gone is fine.
            self._json_or_raise(response)

    @asynccontextmanager
    async def uploaded(self, path: Path) -> AsyncIterator[str]:
        """Upload `path` for the length of the block, then delete it from Meta's storage."""
        file_id = await self.upload_file(path)
        try:
            yield file_id
        finally:
            try:
                await self.delete_file(file_id)
            except Exception:
                logger.warning("Could not delete an uploaded file; it expires within the hour")

    async def count_input_tokens(self, body: Mapping[str, Any], *, policy: DataPolicy) -> int:
        """POST /responses/input_tokens: the request's input tokens, media included, without
        running it. Gated like a paid call because it sends the same data."""
        self._reserve_checks(body, policy=policy)
        response = await self._http.post(
            "responses/input_tokens", headers=self._auth_headers(), json=body
        )
        tokens = self._json_or_raise(response).get("input_tokens")
        if not isinstance(tokens, int):
            raise ModelApiError(response.status_code, "token count response has no input_tokens")
        return tokens

    async def create_response(
        self, body: Mapping[str, Any], *, policy: DataPolicy, worst_case_usd: float, stage: Stage
    ) -> dict[str, Any]:
        """POST /responses without streaming. Records the cost from the response's token usage."""
        model = str(body.get("model"))
        worst_case = [_worst_case(stage, model, worst_case_usd)]
        reservation = self._reserve(body, policy=policy, worst_case_usd=worst_case_usd)
        try:
            response = await self._http.post("responses", headers=self._auth_headers(), json=body)
            self._check_status(response, reservation, worst_case)
            payload = self._json_or_raise(response)
            self._settle(reservation, _token_costs(stage, model, payload, worst_case_usd))
            return payload
        except _NEVER_SENT:
            self._guard.release(reservation)
            raise
        except Exception:
            self._settle(reservation, worst_case)  # Sent, outcome unknown: assume billed.
            raise

    async def stream_response(
        self,
        body: Mapping[str, Any],
        *,
        policy: DataPolicy,
        worst_case_usd: float,
        charge: Sequence[CostEntry],
    ) -> AsyncIterator[dict[str, Any]]:
        """POST /responses with `stream: true`, yielding each server-sent event as a dict.

        `charge` is recorded as soon as the API accepts the request: from then on the call is
        billed, whatever happens to the stream.
        """
        reservation = self._reserve(body, policy=policy, worst_case_usd=worst_case_usd)
        headers = {**self._auth_headers(), "Accept": "text/event-stream"}
        try:
            async with self._http.stream(
                "POST", "responses", headers=headers, json={**body, "stream": True}
            ) as response:
                if response.status_code >= 400:
                    await response.aread()
                self._check_status(response, reservation, charge)
                self._settle(reservation, charge)
                async for event in _server_sent_events(response.aiter_lines()):
                    yield event
        except _NEVER_SENT:
            self._guard.release(reservation)
            raise
        except Exception:
            self._settle(reservation, charge)  # Sent, outcome unknown: assume billed.
            raise

    def _check_status(
        self, response: httpx.Response, reservation: Reservation, charge: Sequence[CostEntry]
    ) -> None:
        """4xx: refused, not billed. 5xx: may have run, so charged at the worst case."""
        if response.status_code < 400:
            return
        if response.status_code < 500:
            self._guard.release(reservation)
        else:
            self._settle(reservation, charge)
        raise ModelApiError(response.status_code, response.text)

    def _settle(self, reservation: Reservation, entries: Sequence[CostEntry]) -> None:
        """Record the cost in the spend ledger and in the running job's costs."""
        if reservation.open:
            costs.record(entries)
        self._guard.settle(reservation, entries)

    def _reserve(
        self, body: Mapping[str, Any], *, policy: DataPolicy, worst_case_usd: float
    ) -> Reservation:
        self._reserve_checks(body, policy=policy)
        return self._guard.reserve(worst_case_usd)

    def _reserve_checks(self, body: Mapping[str, Any], *, policy: DataPolicy) -> None:
        """The data policy and the kill switch, checked before anything is sent."""
        model = body.get("model")
        if not isinstance(model, str):
            raise ValueError("Request body needs a model id.")
        ensure_model_allowed(model, policy)
        self._guard.ensure_enabled()

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key.get_secret_value()}"}

    @staticmethod
    def _json_or_raise(response: httpx.Response) -> dict[str, Any]:
        if response.status_code >= 400:
            raise ModelApiError(response.status_code, response.text)
        payload = response.json()
        if not isinstance(payload, dict):
            raise ModelApiError(response.status_code, "expected a JSON object")
        return payload


async def _server_sent_events(lines: AsyncIterator[str]) -> AsyncIterator[dict[str, Any]]:
    """Group `data:` lines into events (a blank line ends one) and decode them as JSON."""
    data: list[str] = []
    async for line in lines:
        if line.startswith("data:"):
            data.append(line.removeprefix("data:").strip())
        elif not line and data:
            event = _decode_event("\n".join(data))
            data.clear()
            if event is not None:
                yield event
    if data:
        event = _decode_event("\n".join(data))
        if event is not None:
            yield event


def _decode_event(data: str) -> dict[str, Any] | None:
    if data == "[DONE]":
        return None
    event = json.loads(data)
    return event if isinstance(event, dict) else None


def _token_costs(
    stage: Stage, model: str, payload: Mapping[str, Any], worst_case_usd: float
) -> list[CostEntry]:
    """Cost entries from the response's token usage; the worst case when usage is missing."""
    usage = payload.get("usage")
    tokens = usage if isinstance(usage, Mapping) else {}
    input_tokens, output_tokens = tokens.get("input_tokens"), tokens.get("output_tokens")
    if isinstance(input_tokens, int) and isinstance(output_tokens, int):
        try:
            return [
                CostEntry(
                    stage=stage,
                    model=model,
                    unit="input_tokens",
                    quantity=input_tokens,
                    usd=token_cost_usd(model, input_tokens, 0),
                ),
                CostEntry(
                    stage=stage,
                    model=model,
                    unit="output_tokens",
                    quantity=output_tokens,
                    usd=token_cost_usd(model, 0, output_tokens),
                ),
            ]
        except UnknownPriceError:
            pass
    return [_worst_case(stage, model, worst_case_usd)]


def _worst_case(stage: Stage, model: str, usd: float) -> CostEntry:
    return CostEntry(stage=stage, model=model, unit="output_tokens", quantity=0, usd=usd)
