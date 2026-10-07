from __future__ import annotations

from typing import Any, cast

from .._http import HttpPipeline
from ..types.common import FilterResponse
from ..types.thailand import MerchantThailand, MerchantThailandFilterRequest


class ThailandResource:
    """``thailand/*`` — Thai postal areas with courier coverage and surcharge flags."""

    def __init__(self, http: HttpPipeline) -> None:
        self._http = http

    def filter(
        self, request: MerchantThailandFilterRequest, *, timeout: float | None = None
    ) -> FilterResponse[MerchantThailand]:
        """Search postal areas. ``POST thailand/filter``."""
        # older servers return 500 when the array is missing, so always send it
        body: dict[str, Any] = {**request}
        if body.get("shipment_provider_names") is None:
            body["shipment_provider_names"] = []
        return cast(
            "FilterResponse[MerchantThailand]",
            self._http.request("POST", ["thailand", "filter"], auth=True, body=body, timeout=timeout),
        )
