"""The planner interface, an offline planner, and the checks every plan goes through.

A planner only describes the clip: which objects move freely, during which seconds, and
which objects have a known size. It never decides the verdict.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from pisa_contracts import CameraNotes, DataPolicy, IngestResult, Plan, PlanEvent, ReferenceObject
from pisa_contracts.schema import SCHEMA

MAX_EVENTS = 4
MAX_PHRASES_PER_EVENT = 2
MAX_REFERENCES = 3
# Shorter windows hold too few frames to fit a parabola.
MIN_EVENT_S = 0.15
# SAM takes one short concept phrase.
MAX_PHRASE_WORDS = 4
MAX_PHRASE_CHARS = 40
MAX_REFERENCE_SIZE_M = 500.0


class Planner(Protocol):
    async def plan(self, video: Path, ingest: IngestResult, *, policy: DataPolicy) -> Plan:
        """Read a normalized clip and return a checked plan (see `checked`)."""
        ...


class WholeClipPlanner:
    """Offline stand-in: the whole clip is one event with one phrase, and nothing has a scale."""

    def __init__(self, phrase: str) -> None:
        self._phrase = phrase

    async def plan(self, video: Path, ingest: IngestResult, *, policy: DataPolicy) -> Plan:
        return Plan(
            measurable=True,
            reason=None,
            events=[
                PlanEvent(
                    type="fall",
                    start_s=0.0,
                    end_s=_duration_s(ingest),
                    object_phrases=[self._phrase],
                )
            ],
            references=[],
            camera=CameraNotes(motion="unknown", has_cuts=False, slow_motion_suspected=False),
        )


def checked(plan: Plan, ingest: IngestResult, *, margin_s: float = 0.0) -> Plan:
    """Keep only what the later stages can use.

    Windows are clipped to the clip and pulled `margin_s` inside at both ends: a planner that
    sees a few frames per second can place a release or a catch only to within one sampling
    interval, and a window that includes a hand would make a real throw look impossible.
    Phrases are normalized and deduplicated, sizes must be positive and ordered, and a plan
    that claims events but keeps none becomes "too unclear".
    """
    if not plan.measurable:
        return plan.model_copy(
            update={"reason": plan.reason or "no_free_flight", "events": [], "references": []}
        )
    duration = _duration_s(ingest)
    events = []
    for event in plan.events[:MAX_EVENTS]:
        start = max(0.0, event.start_s) + margin_s
        end = min(duration, event.end_s) - margin_s
        phrases = _unique(phrase for p in event.object_phrases if (phrase := _phrase(p)))
        if end - start >= MIN_EVENT_S and phrases:
            events.append(
                event.model_copy(
                    update={
                        "start_s": start,
                        "end_s": end,
                        "object_phrases": phrases[:MAX_PHRASES_PER_EVENT],
                    }
                )
            )
    references = [
        reference.model_copy(update={"phrase": phrase})
        for reference in plan.references[:MAX_REFERENCES]
        if (phrase := _phrase(reference.phrase)) and _plausible(reference)
    ]
    if not events:
        return plan.model_copy(
            update={"measurable": False, "reason": "too_unclear", "events": [], "references": []}
        )
    return plan.model_copy(update={"reason": None, "events": events, "references": references})


def strict_schema(name: str) -> dict[str, Any]:
    """One contract definition as a standalone JSON Schema for structured output.

    Keeps the descriptions (they instruct the model) and the definitions it refers to, and
    drops annotations that only matter to our code generators.
    """
    definitions: Mapping[str, Any] = SCHEMA["$defs"]
    needed: dict[str, Any] = {}

    def collect(node: Any) -> None:
        if isinstance(node, Mapping):
            reference = node.get("$ref")
            if isinstance(reference, str):
                target = reference.removeprefix("#/$defs/")
                if target not in needed:
                    needed[target] = _without_annotations(definitions[target])
                    collect(definitions[target])
            for value in node.values():
                collect(value)
        elif isinstance(node, list):
            for value in node:
                collect(value)

    root = _without_annotations(definitions[name])
    collect(definitions[name])
    return {**root, "$defs": needed} if needed else root


def _without_annotations(node: Any) -> Any:
    if isinstance(node, Mapping):
        return {
            key: _without_annotations(value)
            for key, value in node.items()
            if key not in ("examples", "title", "$id", "$schema")
        }
    if isinstance(node, list):
        return [_without_annotations(value) for value in node]
    return node


def _phrase(text: str) -> str:
    phrase = re.sub(r"\s+", " ", text).strip().strip(".,;:\"'").lower()
    if not phrase or len(phrase) > MAX_PHRASE_CHARS or len(phrase.split()) > MAX_PHRASE_WORDS:
        return ""
    return phrase


def _unique(items: Any) -> list[str]:
    return list(dict.fromkeys(items))


def _plausible(reference: ReferenceObject) -> bool:
    return 0 < reference.size_min_m <= reference.size_max_m <= MAX_REFERENCE_SIZE_M


def _duration_s(ingest: IngestResult) -> float:
    timebase = ingest.timebase
    return timebase.frame_count * timebase.fps_den / timebase.fps_num
