"""Exceptions raised by the SDK. Every one extends :class:`PostwayError`."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class PostwayError(Exception):
    """Base class for every error raised by this SDK."""


class PostwayConfigError(PostwayError):
    """Invalid client options or call arguments (unsafe base URL, header value, timeout or path
    parameter), or a guarded call without an access token. Messages never echo the offending value.
    """


class PostwayApiError(PostwayError):
    """The server answered with a non-2xx status. Error bodies have the shape
    ``{"code", "isSuccess": false, "message", "data": null}``.

    Typical statuses: 400 (validation / business rule), 403 (missing, unknown or expired token),
    404 (public receipt not found), 500 (server error).

    ``body`` (the parsed response: a JSON value, text, or ``None``) is kept out of ``args``,
    ``str()``, ``repr()``, ``vars()`` and pickles; read ``error.body`` explicitly when you need it.
    """

    __slots__ = ("_body",)

    method: str
    #: Request URL with caller-supplied path parameters replaced by ``:name`` placeholders.
    url: str
    #: HTTP status of the response.
    status: int
    #: Body ``code`` from the server envelope, when present (400 or 500 on errors).
    code: int | None
    #: Server messages; validation failures return several.
    messages: list[str]

    def __init__(
        self,
        message: str | None = None,
        *,
        method: str,
        url: str,
        status: int,
        code: int | None = None,
        messages: Sequence[str] = (),
        body: Any = None,
    ) -> None:
        messages = list(messages)
        super().__init__(message or "; ".join(messages) or f"HTTP {status}")
        self.method = method
        self.url = url
        self.status = status
        self.code = code
        self.messages = messages
        self._body = body

    @property
    def body(self) -> Any:
        """Parsed response body (JSON value, text, or ``None``)."""
        return self._body

    def __str__(self) -> str:
        return str(self.args[0])

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}({self.args[0]!r}, method={self.method!r}, url={self.url!r}, "
            f"status={self.status!r}, code={self.code!r})"
        )

    def __reduce__(self) -> tuple[Any, ...]:
        # Rebuild without the body, so pickled errors (multiprocessing, task queues) never carry it.
        kwargs = {
            "method": self.method,
            "url": self.url,
            "status": self.status,
            "code": self.code,
            "messages": self.messages,
        }
        return (_rebuild, (type(self), self.args[0], kwargs))


class PostwayBusinessError(PostwayApiError):
    """The server answered 2xx but its envelope says ``isSuccess: false``. ``order-shipment/create`` and
    ``cancel`` report courier/verification failures this way (with HTTP 201), so the SDK raises
    rather than returning a successful result.
    """


class PostwayRequestError(PostwayError):
    """The request did not complete: network failure, refused redirect, or timeout. The original
    exception is chained as ``__cause__``.
    """

    method: str
    #: Request URL with caller-supplied path parameters replaced by ``:name`` placeholders.
    url: str

    def __init__(self, message: str, *, method: str, url: str) -> None:
        super().__init__(message)
        self.method = method
        self.url = url

    def __reduce__(self) -> tuple[Any, ...]:
        return (_rebuild, (type(self), self.args[0], {"method": self.method, "url": self.url}))


def _rebuild(cls: type[PostwayError], message: str, kwargs: dict[str, Any]) -> PostwayError:
    return cls(message, **kwargs)
