"""Transport abstraction and the HTTP pipeline: URL building, headers, timeout, body parsing and error mapping."""

from __future__ import annotations

import json
import platform
import ssl
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, NamedTuple, Protocol, runtime_checkable
from urllib.parse import quote, urlencode

from ._errors import PostwayApiError, PostwayBusinessError, PostwayConfigError, PostwayError, PostwayRequestError
from ._validation import (
    assert_auth_scheme,
    assert_header_value,
    assert_path_segment,
    assert_timeout,
    normalize_base_url,
)
from ._version import __version__

DEFAULT_TIMEOUT = 60.0
ACCEPT = "application/json, text/plain;q=0.9, */*;q=0.8"

HttpMethod = Literal["GET", "POST"]


def default_user_agent() -> str:
    return f"postway-sdk-python/{__version__} python/{platform.python_version()}"


# ---------------------------------------------------------------- transport


@dataclass(frozen=True)
class TransportRequest:
    """One HTTP request as handed to a :class:`Transport`."""

    method: str
    url: str
    headers: Mapping[str, str]
    body: bytes | None
    #: Seconds; the transport must give up (raising ``TimeoutError``) once it elapses.
    timeout: float


@dataclass(frozen=True)
class TransportResponse:
    """What a :class:`Transport` returns for any HTTP status, including 3xx/4xx/5xx."""

    status: int
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes = b""


@runtime_checkable
class Transport(Protocol):
    """Sends one request. Implementations must not follow redirects and must return error statuses as
    responses rather than raising. Raise ``TimeoutError`` on timeout and any other exception on a
    network failure; the client wraps both in :class:`PostwayRequestError`.
    """

    def send(self, request: TransportRequest) -> TransportResponse: ...


class _RefuseRedirects(urllib.request.HTTPRedirectHandler):
    """Return the 3xx response as-is instead of following it (so ``Authorization`` is never re-sent)."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


class UrllibTransport:
    """Default transport, built on :mod:`urllib.request` (standard library only).

    The timeout applies to each blocking socket operation (connect, each read), not to the request as a
    whole.
    """

    def __init__(self, ssl_context: ssl.SSLContext | None = None) -> None:
        context = ssl_context if ssl_context is not None else ssl.create_default_context()
        self._opener = urllib.request.build_opener(_RefuseRedirects, urllib.request.HTTPSHandler(context=context))

    def send(self, request: TransportRequest) -> TransportResponse:
        req = urllib.request.Request(  # noqa: S310 - the scheme is validated by normalize_base_url
            request.url, data=request.body, headers=dict(request.headers), method=request.method
        )
        try:
            with self._opener.open(req, timeout=request.timeout) as response:
                return TransportResponse(response.status, dict(response.headers.items()), response.read())
        except urllib.error.HTTPError as error:
            with error:
                headers = dict(error.headers.items()) if error.headers is not None else {}
                return TransportResponse(error.code, headers, error.read())

    def close(self) -> None:
        """Nothing to release; ``urllib`` opens one connection per request."""


# ---------------------------------------------------------------- pipeline


class PathParam(NamedTuple):
    """A caller-supplied path segment. ``value`` goes on the wire; errors show ``:name`` instead."""

    name: str
    value: str


PathSegment = str | PathParam


def param(name: str, value: str) -> PathParam:
    """Mark a path segment as caller input so it is validated and redacted from error messages."""
    return PathParam(name, value)


@dataclass(frozen=True)
class _Result:
    status: int
    body: Any
    #: Redacted route URL, not the one sent.
    url: str


class HttpPipeline:
    """Thin wrapper over a :class:`Transport`. Construction validates every value and never echoes it."""

    def __init__(
        self,
        *,
        base_url: str,
        access_token: str | None,
        token_type: str,
        timeout: float,
        transport: Transport,
        user_agent: str,
    ) -> None:
        self._base_url = normalize_base_url(base_url)
        self._access_token = assert_header_value(access_token, "access_token") if access_token is not None else None
        self._token_type = assert_auth_scheme(token_type)
        self._user_agent = assert_header_value(user_agent, "user_agent")
        self._timeout = assert_timeout(timeout)
        self._transport = transport

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def transport(self) -> Transport:
        return self._transport

    def url(self, path: Sequence[PathSegment], query: Mapping[str, str | None] | None = None) -> str:
        """Absolute URL for a call (segments validated and encoded, empty query values dropped)."""
        segments = []
        for segment in path:
            name, value = ("path segment", segment) if isinstance(segment, str) else segment
            segments.append(quote(assert_path_segment(value, name), safe=""))
        url = f"{self._base_url}/{'/'.join(segments)}"
        search = urlencode([(key, value) for key, value in (query or {}).items() if value is not None and value != ""])
        return f"{url}?{search}" if search else url

    def route(self, path: Sequence[PathSegment]) -> str:
        """Route template of a call, e.g. ``receipt/public/:token``."""
        return "/".join(segment if isinstance(segment, str) else f":{segment.name}" for segment in path)

    def route_url(self, path: Sequence[PathSegment]) -> str:
        """``base_url/route``: the URL reported in errors, so caller-supplied values never reach logs."""
        return f"{self._base_url}/{self.route(path)}"

    def request(
        self,
        method: HttpMethod,
        path: Sequence[PathSegment],
        *,
        auth: bool,
        body: Any = None,
        query: Mapping[str, str | None] | None = None,
        timeout: float | None = None,
    ) -> Any:
        """Perform the call and return the parsed body (``None`` for an empty body)."""
        return self._send_checked(method, path, auth=auth, body=body, query=query, timeout=timeout).body

    def request_envelope(
        self,
        method: HttpMethod,
        path: Sequence[PathSegment],
        *,
        auth: bool,
        body: Any = None,
        timeout: float | None = None,
    ) -> Any:
        """Perform a call whose response is an ``HttpBaseResponse`` envelope and return its ``data``.
        A 2xx envelope with ``isSuccess: false`` raises :class:`PostwayBusinessError`.
        """
        result = self._send_checked(method, path, auth=auth, body=body, query=None, timeout=timeout)
        envelope = result.body
        if not isinstance(envelope, dict) or "isSuccess" not in envelope:
            raise PostwayApiError(
                "Unexpected response: expected { code, isSuccess, message, data }",
                method=method,
                url=result.url,
                status=result.status,
                body=envelope,
            )
        if envelope["isSuccess"] is False:
            code, messages = _describe_body(envelope)
            raise PostwayBusinessError(
                method=method, url=result.url, status=result.status, code=code, messages=messages, body=envelope
            )
        return envelope.get("data")

    def _send_checked(
        self,
        method: HttpMethod,
        path: Sequence[PathSegment],
        *,
        auth: bool,
        body: Any,
        query: Mapping[str, str | None] | None,
        timeout: float | None,
    ) -> _Result:
        result = self._send(method, path, auth=auth, body=body, query=query, timeout=timeout)
        if not 200 <= result.status < 300:
            code, messages = _describe_body(result.body)
            raise PostwayApiError(
                method=method, url=result.url, status=result.status, code=code, messages=messages, body=result.body
            )
        return result

    def _send(
        self,
        method: HttpMethod,
        path: Sequence[PathSegment],
        *,
        auth: bool,
        body: Any,
        query: Mapping[str, str | None] | None,
        timeout: float | None,
    ) -> _Result:
        url = self.url(path, query)
        reported_url = self.route_url(path)
        headers = {"Accept": ACCEPT, "User-Agent": self._user_agent}
        if auth:
            if not self._access_token:
                raise PostwayConfigError(
                    f"{method} {self.route(path)} requires a merchant access token; pass access_token to the client"
                )
            headers["Authorization"] = f"{self._token_type} {self._access_token}"
        payload: bytes | None = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        effective_timeout = assert_timeout(timeout) if timeout is not None else self._timeout

        request = TransportRequest(method, url, headers, payload, effective_timeout)
        try:
            response = self._transport.send(request)
        except PostwayError:
            raise
        except Exception as error:
            if _is_timeout(error):
                message = f"{method} {reported_url} timed out after {effective_timeout:g} s"
            else:
                message = f"{method} {reported_url} failed: {_reason(error)}"
            raise PostwayRequestError(message, method=method, url=reported_url) from error

        if 300 <= response.status < 400:
            raise PostwayRequestError(
                f"{method} {reported_url} failed: redirect refused (HTTP {response.status})",
                method=method,
                url=reported_url,
            )
        content_type = _header(response.headers, "content-type")
        return _Result(response.status, _parse_body(response.body, content_type), reported_url)


def _header(headers: Mapping[str, str], name: str) -> str | None:
    for key, value in headers.items():
        if key.lower() == name:
            return value
    return None


def _charset(content_type: str | None) -> str:
    for part in (content_type or "").split(";")[1:]:
        key, _, value = part.strip().partition("=")
        if key.lower() == "charset" and value:
            return value.strip('"')
    return "utf-8"


def _parse_body(raw: bytes, content_type: str | None) -> Any:
    if not raw:
        return None
    try:
        text = raw.decode(_charset(content_type), errors="replace")
    except LookupError:
        text = raw.decode("utf-8", errors="replace")
    if content_type and "json" in content_type.lower():
        try:
            return json.loads(text)
        except ValueError:
            return text
    return text


def _describe_body(body: Any) -> tuple[int | None, list[str]]:
    if isinstance(body, str):
        return None, [body] if body else []
    if not isinstance(body, dict):
        return None, []
    message = body.get("message")
    if isinstance(message, list):
        messages = [str(item) for item in message]
    elif isinstance(message, str) and message:
        messages = [message]
    else:
        messages = []
    code = body.get("code")
    return (code if isinstance(code, int) and not isinstance(code, bool) else None), messages


def _is_timeout(error: BaseException) -> bool:
    if isinstance(error, TimeoutError):
        return True
    return isinstance(error, urllib.error.URLError) and isinstance(error.reason, TimeoutError)


def _reason(error: BaseException) -> str:
    if isinstance(error, urllib.error.URLError) and not isinstance(error, urllib.error.HTTPError):
        return str(error.reason) or type(error).__name__
    return str(error) or type(error).__name__
