"""Muse Spark spike: the planner alone, or the whole pipeline with every real model.

Needs PISA_PAID_CALLS_ENABLED=true in .env; refuses to send anything otherwise. Our own
clips may use the contributor tier (cheaper, and Meta may train on it); user videos never do.

Plan only (one upload and one Muse Spark call, about $0.01 on the contributor tier):
    uv run --group spikes python services/engine/spikes/plan/run_plan.py eval/raw/drop.mov

The whole pipeline: plan, SAM 3.1 per phrase, physics, explanation (about $0.05 for 3 s):
    uv run --group spikes python services/engine/spikes/plan/run_plan.py eval/raw/drop.mov \\
        --full --locale es

Outputs go to services/engine/spikes/out/<name>/ (gitignored).
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pisa_contracts import CostEntry, DataPolicy, Job, Locale
from pisa_engine.explain.explainer import MuseSparkExplainer
from pisa_engine.ingest.normalize import TimeWindow, normalize
from pisa_engine.jobs import StorageJobStore
from pisa_engine.model_api import costs
from pisa_engine.model_api.client import MetaModelApiClient
from pisa_engine.model_api.spend import JsonlSpendLedger, PaidCallsDisabledError, SpendGuard
from pisa_engine.pipeline import PipelineDeps, run_job
from pisa_engine.planning.muse_spark import MuseSparkPlanner
from pisa_engine.render.store import LocalEvidenceStore
from pisa_engine.settings import get_settings
from pisa_engine.storage import LocalStorage
from pisa_engine.tracking.sam import Sam31Segmenter

OUT_ROOT = Path(__file__).resolve().parents[1] / "out"


async def main() -> int:
    args = _parse_args()
    out = OUT_ROOT / (args.name or args.clip.stem)
    out.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    ledger = JsonlSpendLedger(settings.spend_ledger_path)
    guard = SpendGuard(
        enabled=settings.paid_calls_enabled, cap_usd=settings.spend_cap_usd, ledger=ledger
    )
    client = MetaModelApiClient(
        api_key=settings.meta_api_key, base_url=settings.meta_api_base_url, guard=guard
    )
    policy: DataPolicy = "internal" if args.tier == "contributor" else "user"
    planner = MuseSparkPlanner(
        client,
        model=settings.muse_spark_model,
        contributor_model=settings.muse_spark_contributor_model,
    )
    window = TimeWindow(args.start, args.end) if args.end is not None else None
    source = out / "source.mp4"
    ingest = normalize(args.clip, source, window=window)
    duration = ingest.timebase.frame_count * ingest.timebase.fps_den / ingest.timebase.fps_num

    try:
        if not args.full:
            with costs.collecting() as spent:
                plan = await planner.plan(source, ingest, policy=policy)
            (out / "plan.json").write_text(plan.model_dump_json(indent=2))
            print(plan.model_dump_json(indent=2))
        else:
            spent = await _full(args, out, source, client, planner, policy, settings.sam_model)
    except PaidCallsDisabledError:
        print("Paid calls are off. Set PISA_PAID_CALLS_ENABLED=true in .env to run this spike.")
        return 2
    finally:
        await client.aclose()

    plan_input = sum(e.quantity for e in spent if e.stage == "plan" and e.unit == "input_tokens")
    print(f"\nClip: {duration:.2f} s. Plan input tokens: {plan_input:.0f} "
          f"({plan_input / max(duration, 1e-6):.0f} per second of video).")  # fmt: skip
    for entry in spent:
        print(f"  {entry.stage:<8} {entry.model:<28} {entry.unit:<14} {entry.quantity:>8.0f}"
              f"  ${entry.usd:.5f}")  # fmt: skip
    print(f"This run: ${sum(e.usd for e in spent):.4f}. Ledger total: ${ledger.total_usd():.4f}.")
    return 0


async def _full(
    args: argparse.Namespace,
    out: Path,
    source: Path,
    client: MetaModelApiClient,
    planner: MuseSparkPlanner,
    policy: DataPolicy,
    sam_model: str,
) -> list[CostEntry]:
    store = StorageJobStore(LocalStorage(out / "store"))
    deps = PipelineDeps(
        segmenter=Sam31Segmenter(client, model=sam_model),
        store=store,
        planner=planner,
        explainer=MuseSparkExplainer(client),
        evidence=LocalEvidenceStore(out / "evidence"),
    )
    locale: Locale = args.locale
    job = Job(
        id=uuid4(),
        created_at=datetime.now(UTC),
        source="eval",
        locale=locale,
        data_policy=policy,
        status="queued",
        stage=None,
        error=None,
    )
    work_dir = out / "work"
    work_dir.mkdir(exist_ok=True)
    shutil.copy(source, work_dir / "source")
    final = await run_job(job, work_dir / "source", work_dir, deps)
    if final.error is not None:
        print(f"Job failed at {final.error.stage}: {final.error.code}")
        if final.error.code == "paid_calls_disabled":
            raise PaidCallsDisabledError()
        return []
    result = store.get_result(job.id)
    assert result is not None
    (out / "result.json").write_text(result.model_dump_json(indent=2))
    assert result.verdict is not None
    print(f"Verdict: {result.verdict.label} {result.verdict.decisive_tests}")
    print(f"Explanation: {result.explanation.text if result.explanation else '(template)'}")
    return list(result.costs)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0] if __doc__ else None)
    parser.add_argument("clip", type=Path)
    parser.add_argument("--start", type=float, default=0.0)
    parser.add_argument("--end", type=float, help="Trim the clip to [start, end] seconds first.")
    parser.add_argument("--full", action="store_true", help="Run plan, SAM, physics and explain.")
    parser.add_argument("--locale", default="es", choices=["en", "es", "zh-CN", "pt-BR"])
    parser.add_argument(
        "--tier",
        default="contributor",
        choices=["contributor", "standard"],
        help="Contributor is cheaper and only for our own clips (Meta may train on them).",
    )
    parser.add_argument("--name", help="Output folder name (default: the clip's name).")
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
