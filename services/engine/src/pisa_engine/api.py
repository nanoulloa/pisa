"""HTTP API of the engine. Jobs arrive here from the web app and the WhatsApp webhook."""

from __future__ import annotations

from fastapi import FastAPI

from pisa_engine import __version__

app = FastAPI(title="Pisa engine", version=__version__)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
