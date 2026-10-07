"""The default transport against a throwaway loopback server (no external network)."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, ClassVar

import pytest

from postway import PostwayApiError, PostwayMerchantClient, PostwayRequestError


class _Handler(BaseHTTPRequestHandler):
    seen: ClassVar[list[dict[str, Any]]] = []

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _record(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        self.seen.append({"method": self.command, "path": self.path, "headers": dict(self.headers), "body": body})

    def _reply(self, status: int, body: bytes, content_type: str = "application/json; charset=utf-8") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        self._record()
        if self.path == "/merchant/health/ping":
            self._reply(200, b"pong", "text/plain; charset=utf-8")
        elif self.path == "/merchant/shipment-provider/all":
            self.send_response(302)
            self.send_header("Location", "/merchant/health/ping")
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif self.path.startswith("/merchant/receipt/public/"):
            body = {"code": 400, "isSuccess": False, "message": "ไม่พบใบเสร็จ", "data": None}
            self._reply(404, json.dumps(body, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/merchant/order-shipment/get-by-ref/slow":
            time.sleep(1)
            self._reply(200, b"")
        else:
            self._reply(200, b"")

    def do_POST(self) -> None:
        self._record()
        self._reply(201, json.dumps({"code": 200, "isSuccess": True, "message": "ok", "data": None}).encode())


@pytest.fixture
def base_url() -> Iterator[str]:
    _Handler.seen = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/merchant"
    finally:
        server.shutdown()
        server.server_close()


def test_get_returns_text(base_url: str) -> None:
    assert PostwayMerchantClient(base_url=base_url).health.ping() == "pong"
    assert "Authorization" not in _Handler.seen[0]["headers"]


def test_post_sends_json_and_headers(base_url: str) -> None:
    client = PostwayMerchantClient(base_url=base_url, access_token="tok_123")
    client.order_shipments.cancel("TH0001")
    seen = _Handler.seen[0]
    assert seen["method"] == "POST"
    assert seen["path"] == "/merchant/order-shipment/cancel"
    assert seen["headers"]["Authorization"] == "Bearer tok_123"
    assert seen["headers"]["Content-Type"] == "application/json"
    assert json.loads(seen["body"]) == {"tracking_no": "TH0001"}


def test_error_statuses_come_back_as_api_errors(base_url: str) -> None:
    with pytest.raises(PostwayApiError) as caught:
        PostwayMerchantClient(base_url=base_url).receipts.get_public("secret")
    assert (caught.value.status, caught.value.messages) == (404, ["ไม่พบใบเสร็จ"])
    assert caught.value.url == f"{base_url}/receipt/public/:token"


def test_redirects_are_not_followed(base_url: str) -> None:
    client = PostwayMerchantClient(base_url=base_url, access_token="tok_123")
    with pytest.raises(PostwayRequestError, match="redirect refused"):
        client.shipment_providers.all()
    assert [seen["path"] for seen in _Handler.seen] == ["/merchant/shipment-provider/all"]


def test_empty_body_is_none(base_url: str) -> None:
    assert PostwayMerchantClient(base_url=base_url, access_token="t").order_shipments.get_by_ref("x") is None


def test_times_out(base_url: str) -> None:
    client = PostwayMerchantClient(base_url=base_url, access_token="t", timeout=0.2)
    with pytest.raises(PostwayRequestError, match=r"get-by-ref/:ref timed out after 0\.2 s"):
        client.order_shipments.get_by_ref("slow")


def test_connection_refused_is_a_request_error() -> None:
    client = PostwayMerchantClient(base_url="http://127.0.0.1:9/merchant")
    with pytest.raises(PostwayRequestError, match=r"^GET http://127\.0\.0\.1:9/merchant/health/ping failed: "):
        client.health.ping()
