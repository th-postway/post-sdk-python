from __future__ import annotations

from typing import NotRequired, TypedDict

from .common import FilterRequest, IsoDateString

# ---------------------------------------------------------------- read model


class MerchantOrderShipmentParty(TypedDict):
    """``MerchantOrderShipmentDataSender`` / ``…Recipient``."""

    fullname: str
    mobile_phone: str
    address: str
    sub_district: str
    district: str
    province: str
    zip_code: str


class MerchantOrderShipmentDataPackage(TypedDict):
    """``MerchantOrderShipmentDataPackage`` — dimensions in cm, weight in grams."""

    width: float
    length: float
    height: float
    weight: float
    #: The merchant's own reference given at create time.
    my_tracking_no: str
    #: Courier tracking number.
    tracking_no: str
    ref1: str
    ref2: str
    ref3: str


class MerchantOrderShipmentData(TypedDict):
    """One parcel as returned by every order-shipment read (``MerchantOrderShipmentData``)."""

    #: A :class:`~postway.OrderShipmentChannel` value.
    channel: str
    sender: MerchantOrderShipmentParty
    recipient: MerchantOrderShipmentParty
    package: MerchantOrderShipmentDataPackage
    #: A :class:`~postway.OrderStatus` value.
    status: str
    #: A :class:`~postway.OrderShipmentStatus` value.
    order_shipment_status: str
    created_at: IsoDateString
    updated_at: IsoDateString | None
    in_transit_at: IsoDateString | None
    completed_at: IsoDateString | None


#: ``POST order-shipment/filter`` request. ``filter`` is a case-insensitive match against sender and
#: recipient name/phone/address fields, ``my_tracking_no``, ``tracking_no`` and ``ref1..3``.
MerchantOrderShipmentFilterRequest = FilterRequest

# ---------------------------------------------------------------- create


class MerchantOrderShipmentCreateShipping(TypedDict):
    """``MerchantOrderShipmentCreateRequestShipping``."""

    #: A ``name`` from ``shipment_providers.all()``, e.g. ``"Flash"``.
    shipment_provider_name: str
    #: Your own reference for the parcel.
    my_tracking_no: NotRequired[str]
    #: Only for couriers where you already hold a tracking number.
    shipment_provider_tracking_no: NotRequired[str]


class MerchantOrderShipmentCreateSender(TypedDict):
    """``MerchantOrderShipmentCreateRequestSender``."""

    fullname: str
    email: NotRequired[str]
    mobile_phone: str
    #: National ID / passport number, when the courier requires it.
    card_no: NotRequired[str]
    address: str
    sub_district: str
    district: str
    province: str
    zip_code: str


class MerchantOrderShipmentCreateRecipient(TypedDict):
    """``MerchantOrderShipmentCreateRequestRecipient``."""

    fullname: str
    email: NotRequired[str]
    mobile_phone: str
    address: str
    sub_district: str
    district: str
    province: str
    zip_code: str


class MerchantOrderShipmentCreatePackage(TypedDict):
    """``MerchantOrderShipmentCreateRequestPackage`` — dimensions in cm (≥ 1), weight in grams."""

    #: Declared value to insure; ``0`` = no insurance.
    insurance_value: float
    note: NotRequired[str]
    #: A :class:`~postway.FlashArticleCategory`; the server defaults to ``OTHERS`` (99).
    type: NotRequired[int]
    weight: float
    width: float
    height: float
    length: float


class MerchantOrderShipmentCreateProductCod(TypedDict):
    """``MerchantOrderShipmentCreateRequestProductCod``. The COD amount collected from the recipient is the
    sum of ``price_per_item × amount`` over all lines; send an empty list for non-COD parcels.
    """

    name: str
    amount: int
    price_per_item: float


class MerchantOrderShipmentCreateRequest(TypedDict):
    """One parcel to create (``MerchantOrderShipmentCreateRequest``)."""

    shipping: MerchantOrderShipmentCreateShipping
    sender: MerchantOrderShipmentCreateSender
    recipient: MerchantOrderShipmentCreateRecipient
    package: MerchantOrderShipmentCreatePackage
    product_cods: list[MerchantOrderShipmentCreateProductCod]


# ---------------------------------------------------------------- calculate price


class MerchantOrderShipmentCalculatePriceRequest(TypedDict):
    """``POST order-shipment/calculate-price`` request. ``r_*`` = recipient area, ``p_*`` = parcel
    (weight in grams, dimensions in cm, COD and insurance in THB).
    """

    #: A ``name`` from ``shipment_providers.all()``.
    shipment_name: str
    r_sub_district: str
    r_district: str
    r_province: str
    r_zip_code: str
    p_weight: float
    p_width: float
    p_height: float
    p_length: float
    p_cod: float
    p_insurance: float


class PriceInfo(TypedDict):
    """One price line (``PriceInfo``)."""

    #: A :class:`~postway.PriceInfoDescription` value.
    description: str
    #: Price charged to the store.
    price: float
    cost: float
    cashback_cost: float
    is_reward_cashback: bool
    total_affliliate: float


class OrderShipmentPlanDetail(TypedDict):
    """Which plan bracket the price came from (``OrderShipmentPlanDetail``)."""

    #: A :class:`~postway.PlanDetailRegion` value.
    region: str
    #: A :class:`~postway.PlanDetailType` value.
    type: str
    min_boundary: float
    max_boundary: float


class MerchantOrderShipmentCalculatePriceResponse(TypedDict):
    """``MerchantOrderShipmentCalculatePriceResponse``."""

    price_infos: list[PriceInfo]
    plan_detail: OrderShipmentPlanDetail
