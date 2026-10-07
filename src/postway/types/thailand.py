from __future__ import annotations

from typing import NotRequired, TypedDict

from .common import FilterRequest


class MerchantThailandFilterRequest(FilterRequest):
    """``POST thailand/filter`` request (``MerchantThailandFilterRequest``). Field filters are exact
    matches; ``filter`` matches any of sub-district / district / province / zipcode exactly.
    """

    #: Restrict to areas served by these couriers. Omit (or ``[]``) for all couriers.
    shipment_provider_names: NotRequired[list[str]]
    sub_district: NotRequired[str]
    district: NotRequired[str]
    province: NotRequired[str]
    zip_code: NotRequired[str]


class MerchantThailand(TypedDict):
    """One postal area (``MerchantThailand``). Note the response spells it ``zipcode``."""

    shipment_provider_names: list[str]
    sub_district: str
    district: str
    province: str
    zipcode: str
    is_island: bool
    is_tourist: bool
    is_remote_area: bool
