from __future__ import annotations

from typing import cast

from .._http import HttpPipeline, param
from ..types.common import FileHttpResponse
from ..types.labels import MerchantLabelOrderShipmentsRequest


class LabelsResource:
    """``label/*`` — printable shipping labels and receipts, returned as base64 files."""

    def __init__(self, http: HttpPipeline) -> None:
        self._http = http

    def order_shipments(
        self, request: MerchantLabelOrderShipmentsRequest, *, timeout: float | None = None
    ) -> FileHttpResponse:
        """One file containing the labels of every matching parcel. ``POST label/order/shipments``.
        Decode with ``decode_file()``.

        :raises PostwayApiError: (400) when none of ``tracking_nos`` matches a parcel of the store.
        """
        return cast(
            FileHttpResponse,
            self._http.request("POST", ["label", "order", "shipments"], auth=True, body=request, timeout=timeout),
        )

    def receipt(
        self, receipt_no: str, *, receipt_size: str | None = None, timeout: float | None = None
    ) -> FileHttpResponse:
        """A printable receipt by receipt number. ``GET label/receipt/:receipt_no?receipt_size=``.

        ``receipt_size`` takes a :class:`~postway.ReceiptSize` value.
        """
        return cast(
            FileHttpResponse,
            self._http.request(
                "GET",
                ["label", "receipt", param("receipt_no", receipt_no)],
                auth=True,
                query={"receipt_size": receipt_size},
                timeout=timeout,
            ),
        )
