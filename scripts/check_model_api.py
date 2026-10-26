"""Smoke test for the Meta Model API key.

Sends one tiny request to Muse Spark and prints the HTTP status, the reply,
token usage and an estimated cost. The key is read only from MODEL_API_KEY
(the environment, or the repo's .env file) and is never printed. Nothing is
sent unless PISA_PAID_CALLS_ENABLED is true.

Usage: python3 scripts/check_model_api.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
PROMPT = "Reply with exactly one word: ok"
TIMEOUT_S = 60

# USD per 1M tokens (input, output), from dev.meta.ai/docs/pricing-rate-limits on 2026-10-26.
PRICES_PER_MTOK = {
    "muse-spark-1.3": (1.25, 4.25),
    "muse-spark-1.3-contributor": (0.10, 0.20),
}


def load_dotenv(path: Path) -> None:
    """Set variables from a .env file without overriding the real environment."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().removeprefix("export ")
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


def redact(text: str, secret: str) -> str:
    return text.replace(secret, "[REDACTED]") if secret else text


def reply_text(body: dict[str, Any]) -> str:
    """Join the output_text parts of every message item in a Responses API result."""
    return "".join(
        part.get("text", "")
        for item in body.get("output", [])
        if item.get("type") == "message"
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    )


def main() -> int:
    load_dotenv(ENV_FILE)
    if os.environ.get("PISA_PAID_CALLS_ENABLED", "").lower() != "true":
        print(
            "Paid API calls are disabled (PISA_PAID_CALLS_ENABLED is not true). "
            "No request was sent.",
            file=sys.stderr,
        )
        return 3

    api_key = os.environ.get("MODEL_API_KEY", "")
    base_url = os.environ.get("META_MODEL_API_BASE_URL", "").rstrip("/")
    model = os.environ.get("MUSE_SPARK_MODEL", "")

    missing = [
        name
        for name, value in (
            ("MODEL_API_KEY", api_key),
            ("META_MODEL_API_BASE_URL", base_url),
            ("MUSE_SPARK_MODEL", model),
        )
        if not value
    ]
    if missing:
        print(f"Missing values in {ENV_FILE.name}: {', '.join(missing)}", file=sys.stderr)
        return 2

    if not base_url.startswith("https://"):
        print("META_MODEL_API_BASE_URL must be an https:// URL.", file=sys.stderr)
        return 2

    request = urllib.request.Request(  # noqa: S310 (scheme checked above)
        f"{base_url}/responses",
        data=json.dumps({"model": model, "input": PROMPT}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:  # noqa: S310
            status = response.status
            body: dict[str, Any] = json.loads(response.read())
    except urllib.error.HTTPError as error:
        detail = redact(error.read().decode("utf-8", "replace"), api_key)
        print(f"HTTP {error.code}: {detail[:500]}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError) as error:
        print(f"Request failed: {redact(str(error), api_key)}", file=sys.stderr)
        return 1

    usage = body.get("usage") or {}
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    print(f"HTTP {status}, status={body.get('status')}, model={body.get('model')}")
    print(f"Reply: {redact(reply_text(body), api_key)!r}")
    print(f"Tokens: input={input_tokens}, output={output_tokens}")
    if model in PRICES_PER_MTOK:
        price_in, price_out = PRICES_PER_MTOK[model]
        cost = (input_tokens * price_in + output_tokens * price_out) / 1_000_000
        print(f"Estimated cost: ${cost:.6f}")
    return 0 if body.get("status") == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
