from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from .._http import HttpPipeline, PathSegment, param
from ..types.common import FilterResponse
from ..types.order_shipments import (
    MerchantOrderShipmentCalculatePriceRequest,
    MerchantOrderShipmentCalculatePriceResponse,
    MerchantOrderShipmentCreateRequest,
    MerchantOrderShipmentData,
    MerchantOrderShipmentFilterRequest,
)


class OrderShipmentsResource:
    """``order-shipment/*`` — the store's parcels. Every call is scoped to the token's store."""

    def __init__(self, http: HttpPipeline) -> None:
        self._http = http

    def get_by_tracking_no(self, tracking_no: str, *, timeout: float | None = None) -> MerchantOrderShipmentData | None:
        """Find a parcel by courier tracking number; ``None`` when none.
        ``GET order-shipment/get-by-tracking-no/:tracking_no``.
        """
        path: list[PathSegment] = ["order-shipment", "get-by-tracking-no", param("tracking_no", tracking_no)]
        return cast("MerchantOrderShipmentData | None", self._http.request("GET", path, auth=True, timeout=timeout))

    def get_by_ref(self, ref: str, *, timeout: float | None = None) -> MerchantOrderShipmentData | None:
        """Find a parcel whose ``ref1``, ``ref2`` or ``ref3`` equals ``ref``; ``None`` when none.
        ``GET order-shipment/get-by-ref/:ref``.
        """
        path: list[PathSegment] = ["order-shipment", "get-by-ref", param("ref", ref)]
        return cast("MerchantOrderShipmentData | None", self._http.request("GET", path, auth=True, timeout=timeout))

    def filter(
        self, request: MerchantOrderShipmentFilterRequest, *, timeout: float | None = None
    ) -> FilterResponse[MerchantOrderShipmentData]:
        """Page through the store's parcels, newest first. ``POST order-shipment/filter``."""
        return cast(
            "FilterResponse[MerchantOrderShipmentData]",
            self._http.request("POST", ["order-shipment", "filter"], auth=True, body=request, timeout=timeout),
        )

    def create(
        self,
        requests: MerchantOrderShipmentCreateRequest | Sequence[MerchantOrderShipmentCreateRequest],
        *,
        timeout: float | None = None,
    ) -> list[MerchantOrderShipmentData]:
        """Create one or more parcels, book them with the courier and issue the receipt.
        ``POST order-shipment/create``.

        Not idempotent and never retried by the SDK (bar the one replay after a 403 with
        ``get_access_token``, which nothing ran for). The batch stops at the first failure: parcels
        created before it remain, so on :class:`~postway.PostwayBusinessError` look them up by
        ``my_tracking_no`` before resubmitting.

        :returns: the created parcels, including their courier ``tracking_no``.
        :raises PostwayBusinessError: when verification, creation or receipt issue fails.
        """
        body = [requests] if isinstance(requests, Mapping) else list(requests)
        return cast(
            "list[MerchantOrderShipmentData]",
            self._http.request_envelope("POST", ["order-shipment", "create"], auth=True, body=body, timeout=timeout),
        )

    def calculate_price(
        self, request: MerchantOrderShipmentCalculatePriceRequest, *, timeout: float | None = None
    ) -> MerchantOrderShipmentCalculatePriceResponse:
        """Quote the price of one parcel without creating it. ``POST order-shipment/calculate-price``."""
        return cast(
            MerchantOrderShipmentCalculatePriceResponse,
            self._http.request("POST", ["order-shipment", "calculate-price"], auth=True, body=request, timeout=timeout),
        )

    def cancel(self, tracking_no: str, *, timeout: float | None = None) -> None:
        """Cancel a parcel by courier tracking number (not ``my_tracking_no`` or refs).
        ``POST order-shipment/cancel``.

        :raises PostwayApiError: (400) when the parcel is not found.
        :raises PostwayBusinessError: when the cancellation is refused.
        """
        self._http.request_envelope(
            "POST", ["order-shipment", "cancel"], auth=True, body={"tracking_no": tracking_no}, timeout=timeout
        )
