"""One class per Merchant API area; reach them through ``PostwayMerchantClient`` attributes."""

from .auth import AuthResource
from .health import HealthResource
from .labels import LabelsResource
from .order_shipments import OrderShipmentsResource
from .receipts import ReceiptsResource
from .shipment_providers import ShipmentProvidersResource
from .thailand import ThailandResource

__all__ = [
    "AuthResource",
    "HealthResource",
    "LabelsResource",
    "OrderShipmentsResource",
    "ReceiptsResource",
    "ShipmentProvidersResource",
    "ThailandResource",
]
