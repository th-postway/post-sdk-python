"""Public Merchant API base URLs. Pass ``base_url`` to ``PostwayMerchantClient`` for any other host."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Literal

MerchantEnvironment = Literal["production", "sandbox"]

MERCHANT_BASE_URLS: Mapping[str, str] = MappingProxyType(
    {
        "production": "https://post.postway.co.th/merchant",
        # Sandbox environment for integration testing.
        "sandbox": "https://sandbox-post.postway.co.th/merchant",
    }
)
