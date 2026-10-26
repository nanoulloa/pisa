"""HTTP client for Meta Model API (https://dev.meta.ai/docs).

Every request passes two gates before anything leaves the machine: the data
policy (no contributor-tier model for user videos) and the spend guard (kill
switch and budget). The API key is held as a `SecretStr` and only ever placed in
the Authorization header.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import httpx
from pydantic import SecretStr

from pisa_contracts import CostEntry, DataPolicy, Stage
from pisa_engine.model_api.policy import ensure_model_allowed
from pisa_engine.model_api.pricing import UnknownPriceError, token_cost_usd
from pisa_engine.model_api.spend import Reservation, SpendGuard

DEFAULT_TIMEOUT = httpx.Timeout(30.0, read=300.0)


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
        """POST /files. Returns the file id to reference as `file_id`."""
        self._guard.ensure_enabled()
        with path.open("rb") as media:
            response = await self._http.post(
                "files",
                headers=self._auth_headers(),
                data={"purpose": purpose},
                files={"file": (path.name, media, "video/mp4")},
            )
        payload = self._json_or_raise(response)
        file_id = payload.get("id")
        if not isinstance(file_id, str):
            raise ModelApiError(response.status_code, "upload response has no file id")
        return file_id

    async def create_response(
        self, body: Mapping[str, Any], *, policy: DataPolicy, worst_case_usd: float, stage: Stage
    ) -> dict[str, Any]:
        """POST /responses without streaming. Records the cost from the response's token usage."""
        reservation = self._reserve(body, policy=policy, worst_case_usd=worst_case_usd)
        try:
            response = await self._http.post("responses", headers=self._auth_headers(), json=body)
            payload = self._json_or_raise(response)
            self._guard.settle(
                reservation, _token_costs(stage, str(body["model"]), payload, worst_case_usd)
            )
            return payload
        finally:
            self._guard.release(reservation)

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
                    raise ModelApiError(response.status_code, response.text)
                self._guard.settle(reservation, charge)
                async for event in _server_sent_events(response.aiter_lines()):
                    yield event
        finally:
            self._guard.release(reservation)

    def _reserve(
        self, body: Mapping[str, Any], *, policy: DataPolicy, worst_case_usd: float
    ) -> Reservation:
        model = body.get("model")
        if not isinstance(model, str):
            raise ValueError("Request body needs a model id.")
        ensure_model_allowed(model, policy)
        return self._guard.reserve(worst_case_usd)

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
    return [
        CostEntry(stage=stage, model=model, unit="output_tokens", quantity=0, usd=worst_case_usd)
    ]
