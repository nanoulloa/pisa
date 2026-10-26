"""Which models a job's data may be sent to."""

from __future__ import annotations

from pisa_contracts import DataPolicy

CONTRIBUTOR_SUFFIX = "-contributor"


class ContributorTierForbiddenError(PermissionError):
    def __init__(self, model: str) -> None:
        super().__init__(
            f"{model} is a contributor-tier model (Meta may train on what it receives). "
            "Only internal test clips may use it, never user videos."
        )


def ensure_model_allowed(model: str, policy: DataPolicy) -> None:
    if model.endswith(CONTRIBUTOR_SUFFIX) and policy != "internal":
        raise ContributorTierForbiddenError(model)
