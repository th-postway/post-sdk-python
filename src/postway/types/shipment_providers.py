from __future__ import annotations

from typing import TypedDict


class MinMax(TypedDict):
    """A min/max range (``MerchantShipmentProviderDataWidth`` / ``…Height`` / ``…Length``)."""

    min: float
    max: float


class CalculatedRange(MinMax):
    """A range the courier prices on (``…Weight`` / ``…Cubic`` / ``…Dimension``)."""

    is_calculate: bool


class EnabledRange(MinMax):
    """An optional service with limits (``…Cod`` / ``…Insurance``)."""

    enable: bool


class MerchantShipmentProviderFee(TypedDict):
    """``MerchantShipmentProviderDataFee``."""

    cod_postway_to_customer: float
    cod_customer_to_mass: float


class MerchantShipmentProviderData(TypedDict):
    """A courier the store may ship with (``MerchantShipmentProviderData``)."""

    #: Use this value as ``shipment_provider_name`` / ``shipment_name``.
    name: str
    display_name: str
    width: MinMax
    height: MinMax
    length: MinMax
    weight: CalculatedRange
    cubic: CalculatedRange
    dimension: CalculatedRange
    cod: EnabledRange
    insurance: EnabledRange
    fee: MerchantShipmentProviderFee
