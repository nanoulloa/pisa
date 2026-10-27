"""Which implementation of each model stage the settings ask for: offline fakes or Meta's
models. Shared by the API and the eval, so the eval measures exactly what users get."""

from __future__ import annotations

from collections.abc import Callable

from pisa_engine.explain.explainer import Explainer, MuseSparkExplainer, NoExplainer
from pisa_engine.model_api.client import MetaModelApiClient
from pisa_engine.model_api.spend import JsonlSpendLedger, SpendGuard
from pisa_engine.planning.muse_spark import MuseSparkPlanner
from pisa_engine.planning.planner import Planner, WholeClipPlanner
from pisa_engine.settings import Settings
from pisa_engine.tracking.fake import ColorSegmenter
from pisa_engine.tracking.sam import Sam31Segmenter
from pisa_engine.tracking.segmenter import Segmenter

# A factory rather than a client, so offline setups never build one.
ClientFactory = Callable[[], MetaModelApiClient]


def segmenter_for(config: Settings, client: ClientFactory) -> Segmenter:
    if config.segmenter == "fake":
        return ColorSegmenter()
    return Sam31Segmenter(client(), model=config.sam_model)


def planner_for(config: Settings, client: ClientFactory) -> Planner:
    if config.planner == "fake":
        return WholeClipPlanner(config.default_phrase)
    return MuseSparkPlanner(
        client(),
        model=config.muse_spark_model,
        contributor_model=config.muse_spark_contributor_model,
    )


def explainer_for(config: Settings, client: ClientFactory) -> Explainer:
    if config.explainer == "none":
        return NoExplainer()
    return MuseSparkExplainer(
        client(),
        model=config.muse_spark_model,
        contributor_model=config.muse_spark_contributor_model,
    )


def meta_client_for(config: Settings) -> MetaModelApiClient:
    guard = SpendGuard(
        enabled=config.paid_calls_enabled,
        cap_usd=config.spend_cap_usd,
        ledger=JsonlSpendLedger(config.spend_ledger_path),
    )
    return MetaModelApiClient(
        api_key=config.meta_api_key, base_url=config.meta_api_base_url, guard=guard
    )
