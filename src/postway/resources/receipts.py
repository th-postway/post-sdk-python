from __future__ import annotations

import json
from typing import cast

from .._http import HttpPipeline, param
from ..types.receipts import PublicReceiptResponse


class ReceiptsResource:
    """``receipt/*`` — the public receipt behind the QR code printed on receipts.
    No access token is sent; the receipt token in the URL is the credential.
    """

    def __init__(self, http: HttpPipeline) -> None:
        self._http = http

    def get_public(self, token: str, *, timeout: float | None = None) -> PublicReceiptResponse:
        """Receipt data as JSON. ``GET receipt/public/:token``.

        :raises PostwayApiError: (404) when the token is invalid or the receipt is gone.
        """
        return cast(
            PublicReceiptResponse,
            self._http.request("GET", ["receipt", "public", param("token", token)], auth=False, timeout=timeout),
        )

    def get_public_html(self, token: str, *, timeout: float | None = None) -> str:
        """The rendered public receipt page. ``GET receipt/:token``.

        :raises PostwayApiError: (404) when the token is invalid; its ``body`` holds the "not found" page.
        """
        body = self._http.request("GET", ["receipt", param("token", token)], auth=False, timeout=timeout)
        if isinstance(body, str):
            return body
        return "" if body is None else json.dumps(body, ensure_ascii=False, separators=(",", ":"))

    def public_url(self, token: str) -> str:
        """The URL of the public receipt page, e.g. to show or encode as a QR code. Makes no request."""
        return self._http.url(["receipt", param("token", token)])
