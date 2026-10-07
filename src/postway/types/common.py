from __future__ import annotations

from typing import Generic, NotRequired, TypedDict, TypeVar

T = TypeVar("T")

#: ISO-8601 timestamp as serialised by the server.
IsoDateString = str


class FilterRequest(TypedDict):
    """Paging input shared by every ``filter`` endpoint (``FilterBaseRequest``)."""

    #: Free-text search; semantics depend on the endpoint.
    filter: NotRequired[str]
    #: Page size, 1..1,000,000.
    limit: int
    #: 1-based page number. Pages past the end wrap back to page 1 on the server.
    page: int


class FilterResponse(TypedDict, Generic[T]):
    """Paging output shared by every ``filter`` endpoint (``FilterBaseResponse<T>``)."""

    count: int
    limit: int
    page: int
    page_count: int
    data: list[T]


class HttpBaseResponse(TypedDict, Generic[T]):
    """Envelope used by ``order-shipment/create`` / ``cancel`` and by every error body
    (``HttpBaseResponse<T>``). ``code`` is a body code, not the HTTP status.
    """

    code: int
    isSuccess: bool
    #: A string, or a list of messages for request-validation failures.
    message: str | list[str]
    data: T


class FileHttpResponse(TypedDict):
    """A generated file returned as JSON with base64 content (``FileHttpResponse``)."""

    file_name: str
    #: Base64-encoded file bytes; decode with ``decode_file()``.
    content: str
    content_type: str
    content_length: int
