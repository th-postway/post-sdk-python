from __future__ import annotations

from typing import cast

from .._http import HttpPipeline
from ..types.shipment_providers import MerchantShipmentProviderData


class ShipmentProvidersResource:
    """``shipment-provider/*`` — couriers available to the store."""

    def __init__(self, http: HttpPipeline) -> None:
        self._http = http

    def all(self, *, timeout: float | None = None) -> list[MerchantShipmentProviderData]:
        """Active couriers after the store's white/blacklist, sorted by name. ``GET shipment-provider/all``."""
        return cast(
            "list[MerchantShipmentProviderData]",
            self._http.request("GET", ["shipment-provider", "all"], auth=True, timeout=timeout),
        )
