"""Copies the engine's secrets from .env to the Modal secret "pisa-engine".

Prints key names only, never values. The temporary file Modal reads lives in a private
temporary folder that is deleted as soon as the command ends.

    make sync-secrets
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
REQUIRED = ("SUPABASE_URL", "SUPABASE_SECRET_KEY")
WHATSAPP = (
    "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_APP_SECRET",
    "WHATSAPP_WEBHOOK_VERIFY_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
)
OPTIONAL = ("WHATSAPP_GRAPH_API_VERSION", "PISA_PUBLIC_URL")
# Not secret: the browser origins allowed to call the deployed engine.
PRODUCTION_WEB_ORIGINS = (
    "https://pisa-theta.vercel.app,https://pisa-nanos-projects-ace74675.vercel.app"
)


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip('"').strip("'")
        if value:
            values[key.strip()] = value
    return values


def main() -> int:
    env = read_env(ENV_FILE)
    missing = [key for key in REQUIRED if key not in env]
    if missing:
        print(f"Missing in .env: {', '.join(missing)}. Nothing was changed.")
        return 1
    whatsapp = [key for key in WHATSAPP if key in env]
    if whatsapp and len(whatsapp) < len(WHATSAPP):
        absent = sorted(set(WHATSAPP) - set(whatsapp))
        print(f"WhatsApp is half configured; missing: {', '.join(absent)}. Nothing was changed.")
        return 1
    keys = [*REQUIRED, *whatsapp, *(key for key in OPTIONAL if key in env)]
    lines = [f"{key}={env[key]}" for key in keys] + [f"PISA_WEB_ORIGINS={PRODUCTION_WEB_ORIGINS}"]
    with tempfile.TemporaryDirectory() as folder:  # Created readable by this user only.
        secret_file = Path(folder) / "pisa-engine.env"
        secret_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        command = [sys.executable, "-m", "modal", "secret", "create", "pisa-engine"]
        done = subprocess.run(  # noqa: S603 (fixed arguments)
            [*command, "--from-dotenv", str(secret_file), "--force"],
            capture_output=True,
            text=True,
            check=False,
        )
    if done.returncode != 0:
        print("Modal refused the update (its output is not shown, as it may echo values).")
        return done.returncode
    print("Updated the Modal secret pisa-engine with: " + ", ".join([*keys, "PISA_WEB_ORIGINS"]))
    print("Run `make deploy-engine` so new containers read it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
