"""Enum values used on the Merchant API wire, mirrored from the Merchant API's published schema.

String enums are :class:`~enum.StrEnum`, so members compare equal to the plain strings the server
returns (``parcel["order_shipment_status"] == OrderShipmentStatus.IN_TRANSIT``). Response fields are
typed as ``str`` so values the SDK does not know yet still come through.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum


class LabelSize(StrEnum):
    """Label paper size, for ``labels.order_shipments``."""

    SIZE_4X3 = "4x3"
    SIZE_4X4 = "4x4"
    SIZE_4X6 = "4x6"
    SIZE_6X4 = "6x4"
    SIZE_A4 = "A4"
    SIZE_80MM = "80mm"


class LabelOrientation(StrEnum):
    """Label orientation, for ``labels.order_shipments``."""

    PORTRAIT = "Portrait"
    LANDSCAPE = "Landscape"


class ReceiptSize(StrEnum):
    """Receipt paper width, for ``labels.receipt``."""

    R58MM = "58mm"
    R80MM = "80mm"


class FlashArticleCategory(IntEnum):
    """Parcel content category (numeric on the wire), for ``MerchantOrderShipmentCreatePackage.type``."""

    FILE = 0
    DRY_FOOD = 1
    COMMODITY = 2
    DIGITAL_PRODUCT = 3
    CLOTHES = 4
    BOOKS = 5
    AUTO_PARTS = 6
    SHOES_AND_BAGS = 7
    SPORTS_EQUIPMENT = 8
    COSMETICS = 9
    HOUSEHOLD = 10
    FRUIT = 11
    OTHERS = 99


class OrderStatus(StrEnum):
    """Order lifecycle status."""

    PENDING = "pending"
    ON_PROCESS = "on processing"
    COMPLETED = "completed"


class OrderShipmentStatus(StrEnum):
    """Parcel (shipment) status."""

    PREPARED = "Prepared"
    WAIT_FOR_DROP_OFF = "WaitForDropOff"
    IN_TRANSIT = "In-Transit"
    CANCEL = "Cancel"
    COMPLETE = "Complete"
    REJECT = "Reject"
    CLAIM = "Claim"


class OrderShipmentChannel(StrEnum):
    """Channel an order shipment was created through; Merchant API orders are ``API``."""

    V1 = "V1"
    V2 = "V2"
    V3 = "V3"
    UPLOAD_SHEET = "UPLOAD_SHEET"
    API = "API"


class StoreBillingType(StrEnum):
    """How the store pays for shipping."""

    TOP_UP = "Top Up"
    MONTHLY = "Monthly"


class StoreCodType(StrEnum):
    """How the store receives COD money."""

    RECEIPT = "receipt"
    BILLING_TRANSFER = "billing_transfer"


class UserRole(StrEnum):
    ADMIN = "Admin"
    USER = "User"
    PUBLIC = "Public"


class PriceInfoDescription(StrEnum):
    """Price line description (Thai text on the wire)."""

    SHIPMENT = "ค่าขนส่ง"
    INSURANCE = "ค่าประกัน"
    TOURIST = "ค่าพื้นที่ท่องเที่ยว"
    ISLAND = "ค่าพื้นที่เกาะ"
    REMOTE_AREA = "ค่าพื้นที่ห่างไกล"
    COD = "ค่า COD"
    TOP_UP = "เติมเงิน"
    PRODUCT = "ค่าสินค้า"
    PICKUP = "ค่าเรียกรถเข้ารับ"
    OTHER = "อื่นๆ"
    OIL = "ค่าน้ำมัน"
    MOVE = "ค่าบริการเรียกรถ Move"
    SERVICE_CHARGE = "ค่าบริการ"


class PlanDetailRegion(StrEnum):
    """Pricing region: Bangkok or upcountry."""

    BKK = "BKK"
    UPC = "UPC"


class PlanDetailType(StrEnum):
    """What the price plan was calculated on."""

    WEIGHT = "weight"
    DIMENSION = "dimension"
    CUBIC = "cubic"
