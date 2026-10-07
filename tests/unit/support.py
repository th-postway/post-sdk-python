"""Fake transport and response builders: the pytest counterpart of the Node SDK's mock fetch."""

from __future__ import annotations

import json as jsonlib
from dataclasses import dataclass, field
from typing import Any

from postway import PostwayMerchantClient, TransportRequest, TransportResponse

BASE_URL = "https://merchant.test/merchant"
TOKEN = "tok_123"
AUTH = f"Bearer {TOKEN}"

_UNSET: Any = object()


@dataclass
class RecordedCall:
    url: str
    method: str
    headers: dict[str, str]
    body: Any
    timeout: float


@dataclass
class FakeTransport:
    """Answers with queued responses (or raises queued exceptions) in order and records every request."""

    responses: list[TransportResponse | BaseException] = field(default_factory=list)
    calls: list[RecordedCall] = field(default_factory=list)
    closed: bool = False

    def send(self, request: TransportRequest) -> TransportResponse:
        self.calls.append(
            RecordedCall(
                url=request.url,
                method=request.method,
                headers=dict(request.headers),
                body=jsonlib.loads(request.body) if request.body is not None else _UNSET,
                timeout=request.timeout,
            )
        )
        if not self.responses:
            raise AssertionError(f"unexpected request {request.method} {request.url}")
        next_response = self.responses.pop(0)
        if isinstance(next_response, BaseException):
            raise next_response
        return next_response

    def close(self) -> None:
        self.closed = True


def no_body() -> Any:
    """The value ``RecordedCall.body`` holds when nothing was sent."""
    return _UNSET


def json_response(body: Any, status: int = 200) -> TransportResponse:
    """JSON response as the API sends it."""
    return TransportResponse(
        status, {"Content-Type": "application/json; charset=utf-8"}, jsonlib.dumps(body).encode("utf-8")
    )


def empty(status: int = 200) -> TransportResponse:
    """Empty body, which the API sends when a route returns ``null``."""
    return TransportResponse(status, {}, b"")


def text(body: str, status: int = 200, content_type: str = "text/html; charset=utf-8") -> TransportResponse:
    return TransportResponse(status, {"Content-Type": content_type}, body.encode("utf-8"))


def api_error(status: int, message: str | list[str], code: int | None = None) -> TransportResponse:
    """The API's error envelope."""
    if code is None:
        code = 500 if status == 500 else 400
    return json_response({"code": code, "isSuccess": False, "message": message, "data": None}, status)


def setup(
    responses: list[TransportResponse | BaseException] | None = None, **options: Any
) -> tuple[PostwayMerchantClient, FakeTransport]:
    """A client wired to a fake transport that answers with ``responses`` in order."""
    transport = FakeTransport(list(responses or []))
    kwargs: dict[str, Any] = {"base_url": BASE_URL, "access_token": TOKEN, "transport": transport, **options}
    return PostwayMerchantClient(**kwargs), transport


def only(transport: FakeTransport) -> RecordedCall:
    """The single recorded call; fails the test if there were zero or several."""
    assert len(transport.calls) == 1, f"expected exactly 1 request, got {len(transport.calls)}"
    return transport.calls[0]
