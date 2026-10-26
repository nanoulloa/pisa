"""Meta Model API list prices.

Source: https://dev.meta.ai/docs/pricing-rate-limits, checked 2026-10-26.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TokenPrice:
    input_usd_per_mtok: float
    output_usd_per_mtok: float


TOKEN_PRICES: dict[str, TokenPrice] = {
    "muse-spark-1.3": TokenPrice(input_usd_per_mtok=1.25, output_usd_per_mtok=4.25),
    "muse-spark-1.3-contributor": TokenPrice(input_usd_per_mtok=0.10, output_usd_per_mtok=0.20),
}

SAM_USD_PER_1000_FRAMES = 0.20
SAM_MIN_BILLED_FRAMES = 50


class UnknownPriceError(KeyError):
    """No list price for this model, so we cannot bound what a call would cost."""


def sam_billed_frames(frames: int) -> int:
    return max(frames, SAM_MIN_BILLED_FRAMES)


def sam_cost_usd(frames: int) -> float:
    return sam_billed_frames(frames) * SAM_USD_PER_1000_FRAMES / 1000


def token_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    try:
        price = TOKEN_PRICES[model]
    except KeyError as error:
        raise UnknownPriceError(model) from error
    return (
        input_tokens * price.input_usd_per_mtok + output_tokens * price.output_usd_per_mtok
    ) / 1_000_000
