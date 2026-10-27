"""Subscribes the Pisa app to a WhatsApp Business account's messages, then lists the apps
subscribed. The new Meta dashboard does not always do this, and without it the webhook
receives the dashboard's test events but not real messages.

    uv run python scripts/whatsapp_subscribe.py

Reads WHATSAPP_ACCESS_TOKEN and WHATSAPP_BUSINESS_ACCOUNT_ID from .env; prints no secret.
"""

from __future__ import annotations

import sys

import httpx

from pisa_engine.settings import REPO_ROOT, Settings


def main() -> int:
    settings = Settings()
    env = dict(
        line.split("=", 1)
        for line in (REPO_ROOT / ".env").read_text(encoding="utf-8").splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    )
    account = env.get("WHATSAPP_BUSINESS_ACCOUNT_ID", "").strip()
    token = settings.whatsapp_access_token.get_secret_value()
    if not account or not token:
        print("Set WHATSAPP_BUSINESS_ACCOUNT_ID and WHATSAPP_ACCESS_TOKEN in .env first.")
        return 1
    url = f"https://graph.facebook.com/{settings.whatsapp_graph_version}/{account}/subscribed_apps"
    headers = {"Authorization": f"Bearer {token}"}
    subscribed = httpx.post(url, headers=headers, timeout=30)
    print(
        "Subscribe:",
        subscribed.status_code,
        subscribed.json().get("success", subscribed.text[:200]),
    )
    for app in httpx.get(url, headers=headers, timeout=30).json().get("data", []):
        info = app.get("whatsapp_business_api_data", app)
        print("Subscribed app:", info.get("name"), info.get("id"))
    return 0 if subscribed.is_success else 1


if __name__ == "__main__":
    sys.exit(main())
