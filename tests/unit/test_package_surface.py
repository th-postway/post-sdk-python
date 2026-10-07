from __future__ import annotations

import importlib.metadata
import tomllib
from pathlib import Path

import postway

ROOT = Path(__file__).resolve().parents[2]


def test_version_matches_the_installed_metadata() -> None:
    assert postway.__version__ == importlib.metadata.version("th-postway-post-sdk")


def test_pyproject_reads_the_version_from_one_place() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["dynamic"] == ["version"]
    assert pyproject["tool"]["hatch"]["version"]["path"] == "src/postway/_version.py"
    assert pyproject["project"]["dependencies"] == []


def test_every_public_name_resolves() -> None:
    for name in postway.__all__:
        assert hasattr(postway, name), name


def test_public_surface_snapshot() -> None:
    assert sorted(postway.__all__) == sorted(
        [
            "AuthResource",
            "CalculatedRange",
            "EnabledRange",
            "FileHttpResponse",
            "FilterRequest",
            "FilterResponse",
            "FlashArticleCategory",
            "HealthResource",
            "HttpBaseResponse",
            "IsoDateString",
            "LabelOrientation",
            "LabelSize",
            "LabelsResource",
            "MERCHANT_BASE_URLS",
            "MerchantAccountSession",
            "MerchantAccountStore",
            "MerchantAccountUser",
            "MerchantAuthAccountInfoResponse",
            "MerchantEnvironment",
            "MerchantLabelOrderShipmentsRequest",
            "MerchantOrderShipmentCalculatePriceRequest",
            "MerchantOrderShipmentCalculatePriceResponse",
            "MerchantOrderShipmentCreatePackage",
            "MerchantOrderShipmentCreateProductCod",
            "MerchantOrderShipmentCreateRecipient",
            "MerchantOrderShipmentCreateRequest",
            "MerchantOrderShipmentCreateSender",
            "MerchantOrderShipmentCreateShipping",
            "MerchantOrderShipmentData",
            "MerchantOrderShipmentDataPackage",
            "MerchantOrderShipmentFilterRequest",
            "MerchantOrderShipmentParty",
            "MerchantShipmentProviderData",
            "MerchantShipmentProviderFee",
            "MerchantThailand",
            "MerchantThailandFilterRequest",
            "MinMax",
            "OrderShipmentChannel",
            "OrderShipmentPlanDetail",
            "OrderShipmentStatus",
            "OrderShipmentsResource",
            "OrderStatus",
            "PlanDetailRegion",
            "PlanDetailType",
            "PostwayApiError",
            "PostwayBusinessError",
            "PostwayConfigError",
            "PostwayError",
            "PostwayMerchantClient",
            "PostwayRequestError",
            "PriceInfo",
            "PriceInfoDescription",
            "PublicReceiptPriceInfo",
            "PublicReceiptResponse",
            "PublicReceiptShipment",
            "ReceiptSize",
            "ReceiptsResource",
            "ShipmentProvidersResource",
            "StoreBillingType",
            "StoreCodType",
            "ThailandResource",
            "Transport",
            "TransportRequest",
            "TransportResponse",
            "UrllibTransport",
            "UserRole",
            "__version__",
            "decode_file",
        ]
    )


def test_error_hierarchy() -> None:
    assert issubclass(postway.PostwayBusinessError, postway.PostwayApiError)
    for cls in (postway.PostwayApiError, postway.PostwayConfigError, postway.PostwayRequestError):
        assert issubclass(cls, postway.PostwayError)


def test_enum_wire_values() -> None:
    assert postway.LabelSize.SIZE_4X6.value == "4x6"
    assert postway.OrderShipmentStatus.IN_TRANSIT.value == "In-Transit"
    assert postway.StoreBillingType.TOP_UP.value == "Top Up"
    assert postway.PriceInfoDescription.SHIPMENT.value == "ค่าขนส่ง"
    assert postway.FlashArticleCategory.OTHERS.value == 99
    wire: str = "In-Transit"
    assert wire == postway.OrderShipmentStatus.IN_TRANSIT
