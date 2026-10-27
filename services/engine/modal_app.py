"""The engine API on Modal. Deploy with `make deploy-engine`.

Sized for Modal's free $1/month without a payment method: one CPU core, at most two
containers, scale to zero when idle.

Paid Meta API calls are the founder's switch. `make deploy-engine` deploys the free offline
stages (whole-clip planner, color segmenter, templated explanations);
`make deploy-engine PAID=true` deploys SAM 3.1 and Muse Spark behind the kill switch and the
spend cap, whose ledger lives in Supabase so every container shares it.

Secrets come from the Modal secret "pisa-engine" (`make sync-secrets`): the Supabase URL and
key, the WhatsApp keys, the allowed web origins and, for paid calls, MODEL_API_KEY.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import modal

REQUIREMENTS = Path(__file__).parent / "requirements.modal.txt"
# Read where `modal deploy` runs; containers get the result through the image's environment.
PAID = os.environ.get("PISA_DEPLOY_PAID") == "true"


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
            "PISA_SEGMENTER": "sam" if PAID else "fake",
            "PISA_PLANNER": "muse_spark" if PAID else "fake",
            "PISA_EXPLAINER": "muse_spark" if PAID else "none",
            "PISA_PAID_CALLS_ENABLED": "true" if PAID else "false",
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
