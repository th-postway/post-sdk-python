"""Live, read-only checks against a real Merchant API.

    POSTWAY_MERCHANT_BASE_URL=https://sandbox-post.postway.co.th/merchant \\
    POSTWAY_MERCHANT_ACCESS_TOKEN=... make test-integration

Skipped unless both variables are set. Never creates or cancels anything.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime

import pytest

from postway import PostwayApiError, PostwayMerchantClient

BASE_URL = os.environ.get("POSTWAY_MERCHANT_BASE_URL", "")
ACCESS_TOKEN = os.environ.get("POSTWAY_MERCHANT_ACCESS_TOKEN", "")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not BASE_URL or not ACCESS_TOKEN,
        reason="set POSTWAY_MERCHANT_BASE_URL and POSTWAY_MERCHANT_ACCESS_TOKEN",
    ),
]


@pytest.fixture(scope="module")
def client() -> PostwayMerchantClient:
    return PostwayMerchantClient(base_url=BASE_URL, access_token=ACCESS_TOKEN)


def test_health_ping(client: PostwayMerchantClient) -> None:
    assert client.health.ping() == "pong"


def test_auth_account_info(client: PostwayMerchantClient) -> None:
    info = client.auth.account_info()
    assert info["store"]["code"]
    expired = datetime.fromisoformat(info["session"]["expired"].replace("Z", "+00:00"))
    assert expired > datetime.now(UTC)


def test_rejects_an_invalid_token_with_403() -> None:
    anonymous = PostwayMerchantClient(base_url=BASE_URL, access_token="invalid-token")
    with pytest.raises(PostwayApiError) as caught:
        anonymous.auth.account_info()
    assert caught.value.status == 403


def test_shipment_providers_all(client: PostwayMerchantClient) -> None:
    assert isinstance(client.shipment_providers.all(), list)


def test_thailand_filter(client: PostwayMerchantClient) -> None:
    page = client.thailand.filter({"page": 1, "limit": 5})
    assert page["limit"] == 5
    assert len(page["data"]) <= 5


def test_order_shipments_filter(client: PostwayMerchantClient) -> None:
    assert client.order_shipments.filter({"page": 1, "limit": 5})["count"] >= 0


def test_get_by_tracking_no_returns_none_for_an_unknown_number(client: PostwayMerchantClient) -> None:
    assert client.order_shipments.get_by_tracking_no(f"SDK-NOPE-{int(time.time() * 1000)}") is None
