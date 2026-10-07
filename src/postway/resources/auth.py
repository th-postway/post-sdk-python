from __future__ import annotations

from typing import cast

from .._http import HttpPipeline
from ..types.auth import MerchantAuthAccountInfoResponse


class AuthResource:
    """``auth/*`` — session introspection."""

    def __init__(self, http: HttpPipeline) -> None:
        self._http = http

    def account_info(self, *, timeout: float | None = None) -> MerchantAuthAccountInfoResponse:
        """The store, owner and session expiry behind the access token. ``POST auth/account/info``."""
        return cast(
            MerchantAuthAccountInfoResponse,
            self._http.request("POST", ["auth", "account", "info"], auth=True, timeout=timeout),
        )
