"""The engine API on Modal. Deploy with `make deploy-engine`.

Sized for Modal's free $1/month without a payment method: one CPU core, at most two
containers, scale to zero when idle. Paid Meta API calls stay off here until the spend
ledger moves to Supabase (a local ledger would not be shared between containers).

Secrets come from the Modal secret "pisa-engine": SUPABASE_URL, SUPABASE_SECRET_KEY and
PISA_WEB_ORIGINS.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import modal

REQUIREMENTS = Path(__file__).parent / "requirements.modal.txt"


def _pinned_requirements() -> list[str]:
    """Exact versions exported from uv.lock by `make deploy-engine`.

    Containers import this module again at startup, where the file does not exist and the
    image is already built, so it is only read on the machine that deploys.
    """
    if not modal.is_local():
        return []
    lines = REQUIREMENTS.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]


image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg")
    .uv_pip_install(*_pinned_requirements())
    .env(
        {
            "PISA_SEGMENTER": "fake",
            "PISA_PLANNER": "fake",
            "PISA_EXPLAINER": "none",
            "PISA_PAID_CALLS_ENABLED": "false",
            "PISA_DATA_DIR": "/root/pisa-data",
            "PISA_SPEND_LEDGER_PATH": "/root/pisa-data/spend.jsonl",
            # Modal passes the real client address as the connection peer and drops forged
            # X-Forwarded-For headers (checked 2026-10-26), so forwarded headers stay untrusted.
            "PISA_TRUST_PROXY": "false",
        }
    )
    .add_local_python_source("pisa_engine", "pisa_contracts")
)

app = modal.App("pisa-engine", image=image)


@app.function(
    secrets=[modal.Secret.from_name("pisa-engine")],
    cpu=1.0,
    memory=2048,
    timeout=300,
    max_containers=2,
    scaledown_window=120,
)
@modal.concurrent(max_inputs=8)
@modal.asgi_app()
def web() -> Any:
    from pisa_engine.api import create_app

    return create_app()


@app.function(
    secrets=[modal.Secret.from_name("pisa-engine")],
    schedule=modal.Period(hours=1),
    cpu=0.25,
    memory=512,
    timeout=120,
)
def delete_expired_evidence() -> None:
    """Evidence videos show the user's frames, so they are deleted 24 hours after the check.
    WhatsApp message ids are forgotten once Meta has stopped retrying deliveries."""
    from pisa_engine.api import sweep_expired
    from pisa_engine.settings import get_settings

    sweep_expired(get_settings())
