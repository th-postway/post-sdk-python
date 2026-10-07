"""Runnable version of the README Quick start. See demo/README.md.

    uv run python demo/quick_start.py

Read-only by default and pointed at sandbox. Creating a parcel and printing its label needs
POSTWAY_DEMO_CREATE=1 and only ever runs against the sandbox base URL.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from postway import (
    MERCHANT_BASE_URLS,
    LabelOrientation,
    LabelSize,
    PostwayApiError,
    PostwayBusinessError,
    PostwayMerchantClient,
    decode_file,
)

ACCESS_TOKEN = os.environ.get("POSTWAY_ACCESS_TOKEN") or os.environ.get("POSTWAY_MERCHANT_ACCESS_TOKEN")
BASE_URL = os.environ.get("POSTWAY_MERCHANT_BASE_URL") or MERCHANT_BASE_URLS["sandbox"]
CREATE_ENABLED = os.environ.get("POSTWAY_DEMO_CREATE") == "1"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def run(client: PostwayMerchantClient) -> int:
    # 1. Public endpoint: works without a token.
    print(f"Base URL: {client.base_url}")
    print("health.ping ->", client.health.ping())

    if not ACCESS_TOKEN:
        print(
            "Set POSTWAY_ACCESS_TOKEN (or POSTWAY_MERCHANT_ACCESS_TOKEN) to run the authenticated steps.",
            file=sys.stderr,
        )
        return 1

    # 2. Who am I?
    account = client.auth.account_info()
    print(f"Store: {account['store']['name']}, token expires {account['session']['expired']}")

    # 3. Couriers this store may use.
    providers = client.shipment_providers.all()
    print("Couriers:", ", ".join(provider["name"] for provider in providers) or "(none)")

    # 4. Thai postal areas for one zip code.
    areas = client.thailand.filter({"page": 1, "limit": 5, "zip_code": "10500"})
    for area in areas["data"]:
        print(f"Area: {area['sub_district']} / {area['district']} / {area['province']} {area['zipcode']}")

    # 5. The store's latest parcels (status only).
    parcels = client.order_shipments.filter({"page": 1, "limit": 5})
    print(f"Parcels: {parcels['count']} in total")
    for row in parcels["data"]:
        print(f"  - {row['order_shipment_status']}")

    if not CREATE_ENABLED:
        print("Read-only run complete. Set POSTWAY_DEMO_CREATE=1 to create a sandbox parcel and print its label.")
        return 0
    if client.base_url != MERCHANT_BASE_URLS["sandbox"]:
        print(
            "POSTWAY_DEMO_CREATE=1 only runs against the sandbox base URL; refusing to create a parcel.",
            file=sys.stderr,
        )
        return 1

    # 6. Create a parcel (not idempotent: the SDK never retries it).
    [parcel] = client.order_shipments.create(
        {
            "shipping": {
                "shipment_provider_name": providers[0]["name"] if providers else "Flash",
                "my_tracking_no": f"DEMO-{int(time.time() * 1000)}",
            },
            "sender": {
                "fullname": "My Shop",
                "mobile_phone": "0811111111",
                "address": "1 Silom Rd",
                "sub_district": "สีลม",
                "district": "บางรัก",
                "province": "กรุงเทพมหานคร",
                "zip_code": "10500",
            },
            "recipient": {
                "fullname": "Customer",
                "mobile_phone": "0822222222",
                "address": "2 Nimman Rd",
                "sub_district": "สุเทพ",
                "district": "เมืองเชียงใหม่",
                "province": "เชียงใหม่",
                "zip_code": "50200",
            },
            "package": {"insurance_value": 0, "weight": 500, "width": 10, "length": 20, "height": 5},
            "product_cods": [],  # empty = not COD
        }
    )
    print(f"Created parcel {parcel['package']['my_tracking_no']} ({parcel['order_shipment_status']})")

    # 7. Print its label.
    label = client.labels.order_shipments(
        {
            "tracking_nos": [parcel["package"]["tracking_no"]],
            "label_size": LabelSize.SIZE_4X6,
            "label_orientation": LabelOrientation.PORTRAIT,
        }
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Path(...).name keeps a server-supplied name from escaping the output directory.
    label_path = OUTPUT_DIR / Path(label["file_name"]).name
    label_path.write_bytes(decode_file(label))
    print(f"Label saved to {label_path}")
    return 0


def main() -> int:
    # never hardcode the token
    with PostwayMerchantClient(base_url=BASE_URL, access_token=ACCESS_TOKEN) as client:
        try:
            return run(client)
        except PostwayBusinessError as error:
            print("Refused by the API:", error.messages, file=sys.stderr)
        except PostwayApiError as error:
            if error.status != 403:
                raise
            print("HTTP 403: the access token is missing, unknown or expired.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
