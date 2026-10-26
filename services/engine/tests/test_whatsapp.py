"""The WhatsApp bot against a fake Graph API: signatures, parsing, language, replies, limits."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

import pisa_contracts as contracts
from pisa_engine.api import create_app
from pisa_engine.explain.keys import explanation_key
from pisa_engine.physics.results import result
from pisa_engine.settings import Settings
from pisa_engine.synthetic import BallScene, render
from pisa_engine.whatsapp.copy import text
from pisa_engine.whatsapp.graph import GraphClient, GraphError, MediaTooLargeError
from pisa_engine.whatsapp.inbound import detect_locale, messages, valid_signature
from pisa_engine.whatsapp.ledger import MemoryMessageLedger, SupabaseMessageLedger

pytestmark = pytest.mark.anyio

APP_SECRET = "test-app-secret"  # noqa: S105 (a test value, not a credential)
VERIFY_TOKEN = "test-verify-token"  # noqa: S105
PHONE_ID = "106540352242922"
GRAPH = "https://graph.facebook.com/v26.0"
MEDIA_URL = "https://lookaside.fbsbx.com/whatsapp_business/attachments/?mid=1"


def _sign(body: bytes, secret: str = APP_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _delivery(*items: dict[str, Any], statuses: bool = False) -> dict[str, Any]:
    value: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "metadata": {"display_phone_number": "15550783881", "phone_number_id": PHONE_ID},
        "contacts": [{"profile": {"name": "Abuela"}, "wa_id": "5215512345678"}],
        "messages": list(items),
    }
    if statuses:
        value = {"messaging_product": "whatsapp", "statuses": [{"id": "wamid.x", "status": "read"}]}
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "102290129340398", "changes": [{"field": "messages", "value": value}]}],
    }


def _video(message_id: str, sender: str = "5215512345678", **extra: Any) -> dict[str, Any]:
    return {
        "from": sender,
        "id": message_id,
        "timestamp": "1744344496",
        "type": "video",
        "video": {"mime_type": "video/mp4", "sha256": "abc", "id": "media-1", "caption": ""},
        **extra,
    }


# Signature, parsing and language


def test_only_deliveries_signed_with_the_app_secret_are_valid() -> None:
    body = json.dumps(_delivery(_video("wamid.1"))).encode()
    assert valid_signature(body, _sign(body), APP_SECRET)
    assert not valid_signature(body, _sign(body, "another-secret"), APP_SECRET)
    assert not valid_signature(body + b" ", _sign(body), APP_SECRET)
    assert not valid_signature(body, None, APP_SECRET)
    assert not valid_signature(body, _sign(body), "")


def test_messages_are_read_from_a_delivery() -> None:
    document = {
        "from": "5511987654321",
        "id": "wamid.2",
        "type": "document",
        "document": {"mime_type": "video/quicktime", "id": "media-2", "caption": "é real?"},
        "context": {"forwarded": True, "frequently_forwarded": True},
    }
    greeting = {"from": "8613800138000", "id": "wamid.3", "type": "text", "text": {"body": "你好"}}
    photo = {"from": "15551234567", "id": "wamid.4", "type": "image", "image": {"id": "m"}}
    video, doc, hello, image = messages(_delivery(_video("wamid.1"), document, greeting, photo))
    assert (video.kind, video.media_id, video.sender) == ("video", "media-1", "5215512345678")
    assert (doc.kind, doc.media_id, doc.text, doc.frequently_forwarded) == (
        "video",
        "media-2",
        "é real?",
        True,
    )
    assert (hello.kind, hello.text) == ("text", "你好")
    assert image.kind == "other"
    assert list(messages(_delivery(statuses=True))) == []
    assert list(messages({"object": "page"})) == []


@pytest.mark.parametrize(
    ("sender", "words", "locale"),
    [
        ("5215512345678", "", "es"),  # Mexico.
        ("50688887777", "", "es"),  # Costa Rica.
        ("18095551234", "", "es"),  # Dominican Republic, inside +1.
        ("5511987654321", "", "pt-BR"),
        ("8613800138000", "", "zh-CN"),
        ("15551234567", "", "en"),
        ("15551234567", "¿esto es real?", "es"),  # Their words win over their number.
        ("5215512345678", "is this real?", "en"),
        ("15551234567", "isso é verdade? você viu?", "pt-BR"),
        ("5215512345678", "这是真的吗", "zh-CN"),
    ],
)
def test_the_reply_language(sender: str, words: str, locale: str) -> None:
    assert detect_locale(sender, words) == locale


def test_explanation_rule_matches_the_web_app() -> None:
    """The same cases as apps/web/src/lib/result.test.ts."""

    def verdict(label: str, decisive: list[str], reason: str | None = None) -> contracts.Verdict:
        return contracts.Verdict.model_validate(
            {
                "label": label,
                "policy_version": "0.1.0",
                "decisive_tests": decisive,
                "reason_code": reason,
            }
        )

    tests = [
        result("free_fall_shape", "violation", 0.7, [], "acceleration_grows"),
        result("galileo_pair", "violation", 1.0, [], "pair_falls_apart"),
    ]
    assert (
        explanation_key(verdict("physically_impossible", ["galileo_pair"]), tests)
        == "pair_falls_apart"
    )
    gravity = [
        result("free_fall_shape", "pass", 1.0, []),
        result("implied_g", "violation", 0.9, [], "gravity_too_weak"),
    ]
    assert (
        explanation_key(verdict("inconclusive", [], "weak_violation"), gravity)
        == "gravity_too_weak"
    )
    assert explanation_key(verdict("inconclusive", [], "too_unclear"), []) == "too_unclear"


def test_copy_fills_its_arguments_in_every_language() -> None:
    for locale in ("en", "es", "zh-CN", "pt-BR"):
        assert "https://x.test" in text(locale, "WhatsApp.details", link="https://x.test")
    assert text("es", "Verdict.inconclusive") == "No concluyente"


# Graph API client


class FakeGraph:
    """Answers the Graph API calls the bot makes and records them."""

    def __init__(self, clip: bytes = b"", *, file_size: int | None = None) -> None:
        self.requests: list[httpx.Request] = []
        self.clip = clip
        self.file_size = len(clip) if file_size is None else file_size
        self.fail_next: list[int] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.fail_next:
            return httpx.Response(self.fail_next.pop(0), json={"error": {"message": "busy"}})
        path = request.url.path
        if request.url.host == "lookaside.fbsbx.com":
            return httpx.Response(200, content=self.clip, headers={"content-type": "video/mp4"})
        if path.endswith("/messages"):
            return httpx.Response(
                200, json={"messaging_product": "whatsapp", "messages": [{"id": "wamid.out"}]}
            )
        if path.endswith("/media"):
            return httpx.Response(200, json={"id": "media-out"})
        return httpx.Response(
            200,
            json={
                "url": MEDIA_URL,
                "mime_type": "video/mp4",
                "file_size": self.file_size,
                "id": "media-1",
            },
        )

    def sent(self) -> list[dict[str, Any]]:
        return [json.loads(r.content) for r in self.requests if r.url.path.endswith("/messages")]


def _graph(fake: Callable[[httpx.Request], httpx.Response]) -> GraphClient:
    async def no_wait(_seconds: float) -> None:
        return None

    return GraphClient(
        access_token=SecretStr("EAA-not-a-real-token"),
        phone_number_id=PHONE_ID,
        transport=httpx.MockTransport(fake),
        sleep=no_wait,
    )


async def test_graph_requests_follow_the_cloud_api(tmp_path: Path) -> None:
    fake = FakeGraph(b"\x00" * 100)
    graph = _graph(fake)
    info = await graph.media_info("media-1")
    assert (info.url, info.mime_type, info.file_size) == (MEDIA_URL, "video/mp4", 100)
    lookup = fake.requests[-1]
    assert str(lookup.url) == f"{GRAPH}/media-1?phone_number_id={PHONE_ID}"
    assert lookup.headers["authorization"] == "Bearer EAA-not-a-real-token"

    assert await graph.download(info.url, tmp_path / "v.mp4") == 100
    assert fake.requests[-1].headers["authorization"] == "Bearer EAA-not-a-real-token"
    with pytest.raises(MediaTooLargeError):
        await graph.download(info.url, tmp_path / "big.mp4", max_bytes=50)
    assert not (tmp_path / "big.mp4").exists()

    (tmp_path / "e.mp4").write_bytes(b"mp4")
    assert await graph.upload_media(tmp_path / "e.mp4", "video/mp4") == "media-out"
    upload = fake.requests[-1]
    assert upload.url.path == f"/v26.0/{PHONE_ID}/media"
    form = upload.content.decode("latin-1")
    assert 'name="messaging_product"\r\n\r\nwhatsapp' in form
    assert 'name="type"\r\n\r\nvideo/mp4' in form

    await graph.send_video("5215512345678", "media-out", "*Físicamente imposible*")
    assert fake.sent()[-1] == {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "5215512345678",
        "type": "video",
        "video": {"id": "media-out", "caption": "*Físicamente imposible*"},
    }


async def test_only_calls_that_cannot_double_send_are_retried() -> None:
    fake = FakeGraph()
    graph = _graph(fake)
    fake.fail_next = [429]  # Throttled before arriving: safe to repeat a send.
    await graph.send_text("15551234567", "hi")
    assert len(fake.sent()) == 2
    fake.fail_next = [500]  # May have arrived: a second send could duplicate the message.
    with pytest.raises(GraphError):
        await graph.send_text("15551234567", "hi")
    assert len(fake.sent()) == 3
    fake.fail_next = [503, 503]  # Looking up media is safe to repeat.
    await graph.media_info("media-1")


# The ledger


def test_each_message_id_is_claimed_once() -> None:
    ledger = MemoryMessageLedger()
    assert ledger.claim("wamid.1")
    assert not ledger.claim("wamid.1")
    assert ledger.claim("wamid.2")


def test_supabase_ledger_inserts_ignoring_duplicates() -> None:
    requests: list[httpx.Request] = []
    rows: list[list[dict[str, str]]] = [[{"id": "wamid.1"}], []]

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return (
            httpx.Response(201, json=rows.pop(0))
            if request.method == "POST"
            else httpx.Response(204)
        )

    ledger = SupabaseMessageLedger(
        "https://project.supabase.co", SecretStr("sb_secret_not-real"), httpx.MockTransport(respond)
    )
    assert ledger.claim("wamid.1")
    assert not ledger.claim("wamid.1")
    insert = requests[0]
    assert insert.url.path == "/rest/v1/whatsapp_messages"
    assert insert.headers["prefer"] == "resolution=ignore-duplicates,return=representation"
    assert json.loads(insert.content) == {"id": "wamid.1"}


# The whole conversation, through the API and the real pipeline


@pytest.fixture(scope="module")
def eased_clip(tmp_path_factory: pytest.TempPathFactory) -> bytes:
    path = tmp_path_factory.mktemp("clips") / "eased.mp4"
    render(BallScene(profile="eased", hold_s=0.15, duration_s=0.75, vx_mps=0.8), path)
    return path.read_bytes()


def _app(tmp_path: Path, fake: FakeGraph, **overrides: Any) -> TestClient:
    settings = Settings(
        _env_file=None,
        PISA_DATA_DIR=str(tmp_path / "data"),
        WHATSAPP_APP_SECRET=APP_SECRET,
        WHATSAPP_WEBHOOK_VERIFY_TOKEN=VERIFY_TOKEN,
        PISA_PUBLIC_URL="https://pisa.test",
        **overrides,
    )
    return TestClient(create_app(settings, graph=_graph(fake)))


def _post(client: TestClient, payload: dict[str, Any]) -> httpx.Response:
    body = json.dumps(payload).encode()
    response: httpx.Response = client.post(
        "/whatsapp/webhook",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": _sign(body)},
    )
    return response


def test_meta_can_subscribe_with_the_verify_token(tmp_path: Path) -> None:
    client = _app(tmp_path, FakeGraph())
    query = {
        "hub.mode": "subscribe",
        "hub.challenge": "1158201444",
        "hub.verify_token": VERIFY_TOKEN,
    }
    ok = client.get("/whatsapp/webhook", params=query)
    assert (ok.status_code, ok.text) == (200, "1158201444")
    wrong = client.get("/whatsapp/webhook", params={**query, "hub.verify_token": "guess"})
    assert wrong.status_code == 403


def test_a_forwarded_video_gets_an_acknowledgment_then_the_evidence(
    tmp_path: Path, eased_clip: bytes
) -> None:
    fake = FakeGraph(eased_clip)
    client = _app(tmp_path, fake)
    forwarded = _video("wamid.1", context={"forwarded": True, "frequently_forwarded": True})
    response = _post(client, _delivery(forwarded))
    assert response.json() == {"status": "received"}

    acknowledgment, reply = fake.sent()
    assert acknowledgment["text"]["body"] == text("es", "WhatsApp.received")  # A Mexican number.
    assert reply["type"] == "video"
    assert reply["video"]["id"] == "media-out"
    caption = reply["video"]["caption"]
    assert caption.startswith("*Físicamente imposible*\n\n")
    assert text("es", "Explanations.slows_down_while_falling") in caption
    assert text("es", "WhatsApp.frequentlyForwarded") in caption
    assert text("es", "WhatsApp.legend.fit") in caption
    assert "https://pisa.test/es/result/" in caption
    assert len(caption) <= 1024
    # The work folder (download, normalized clip, evidence) is gone.
    assert not any((tmp_path / "data" / "work").iterdir())

    # Meta retries the same delivery: nothing is checked or sent twice.
    _post(client, _delivery(forwarded))
    assert len(fake.sent()) == 2


def test_other_messages_get_guidance(tmp_path: Path) -> None:
    fake = FakeGraph()
    client = _app(tmp_path, fake)
    hello = {"from": "15551234567", "id": "wamid.5", "type": "text", "text": {"body": "hello"}}
    photo = {"from": "5511987654321", "id": "wamid.6", "type": "image", "image": {"id": "m"}}
    _post(client, _delivery(hello, photo))
    welcome, only_videos = fake.sent()
    assert welcome["text"]["body"] == text("en", "WhatsApp.welcome")
    assert only_videos["text"]["body"] == text("pt-BR", "WhatsApp.onlyVideos")


def test_videos_over_16_mb_are_not_downloaded(tmp_path: Path) -> None:
    fake = FakeGraph(file_size=20 * 1024 * 1024)
    client = _app(tmp_path, fake)
    _post(client, _delivery(_video("wamid.7")))
    (reply,) = fake.sent()
    assert reply["text"]["body"] == text("es", "WhatsApp.tooLarge")
    assert not any(r.url.host == "lookaside.fbsbx.com" for r in fake.requests)


def test_each_number_has_a_limit(tmp_path: Path) -> None:
    fake = FakeGraph(file_size=20 * 1024 * 1024)  # Refused after the limit check, cheaply.
    client = _app(tmp_path, fake, PISA_JOBS_PER_HOUR=1)
    _post(client, _delivery(_video("wamid.8")))
    _post(client, _delivery(_video("wamid.9")))
    assert fake.sent()[-1]["text"]["body"] == text("es", "WhatsApp.rateLimited")


def test_unsigned_or_unconfigured_deliveries_are_refused(tmp_path: Path) -> None:
    fake = FakeGraph()
    token = "engine-token"  # noqa: S105 (a test value). Meta never sends it.
    client = _app(tmp_path, fake, PISA_ENGINE_TOKEN=token)
    body = json.dumps(_delivery(_video("wamid.10"))).encode()
    forged = client.post(
        "/whatsapp/webhook", content=body, headers={"X-Hub-Signature-256": _sign(body, "x")}
    )
    assert forged.status_code == 401
    assert _post(client, _delivery()).status_code == 200  # Signed: no engine token needed.
    assert fake.requests == []
    plain = TestClient(create_app(Settings(_env_file=None, PISA_DATA_DIR=str(tmp_path / "plain"))))
    assert plain.post("/whatsapp/webhook", content=b"{}").status_code == 404
