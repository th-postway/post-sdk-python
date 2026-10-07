from __future__ import annotations

from typing import TypedDict

from .common import IsoDateString


class PublicReceiptPriceInfo(TypedDict):
    """A price line on the public receipt (no cost fields)."""

    description: str
    price: float


class PublicReceiptShipment(TypedDict):
    """A parcel on the public receipt (``PublicReceiptShipment``)."""

    seq: int
    shipment_provider_name: str
    tracking_no: str
    recipient_fullname: str
    recipient_mobile_phone_masked: str
    recipient_province: str
    recipient_zip_code: str
    weight: float
    width: float
    length: float
    height: float
    cod: float
    #: A :class:`~postway.OrderShipmentStatus` value.
    status: str
    status_text: str
    created_at: IsoDateString | None
    in_transit_at: IsoDateString | None
    completed_at: IsoDateString | None
    in_transit_at_text: str
    completed_at_text: str
    price_infos: list[PublicReceiptPriceInfo]


class PublicReceiptResponse(TypedDict):
    """``GET receipt/public/:token`` response (``PublicReceiptResponse``)."""

    #: ``False`` when the whole receipt was cancelled.
    is_available: bool
    message: str
    no: str
    #: Formatted ``yyyy/MM/dd HH:mm:ss`` (not ISO).
    created_at: str
    store_name: str
    is_show_public_receipt_store_name: bool
    is_show_public_receipt_header: bool
    is_show_public_receipt_package_detail: bool
    is_show_public_receipt_total: bool
    price_discount: float
    price_total: float
    price_get_total: float
    price_charge_total: float
    shipments: list[PublicReceiptShipment]
