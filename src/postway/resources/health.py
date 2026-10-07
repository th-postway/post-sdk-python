from __future__ import annotations

import json

from .._http import HttpPipeline


class HealthResource:
    """``health/*`` — liveness."""

    def __init__(self, http: HttpPipeline) -> None:
        self._http = http

    def ping(self, *, timeout: float | None = None) -> str:
        """Returns ``"pong"`` when the Merchant API is reachable. ``GET health/ping``, no auth."""
        body = self._http.request("GET", ["health", "ping"], auth=False, timeout=timeout)
        if isinstance(body, str):
            return body
        return "" if body is None else json.dumps(body, ensure_ascii=False, separators=(",", ":"))
