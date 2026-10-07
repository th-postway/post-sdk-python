from __future__ import annotations

from collections.abc import Callable

import pytest

from postway import (
    FlashArticleCategory,
    MerchantOrderShipmentCalculatePriceRequest,
    MerchantOrderShipmentCreateRequest,
    MerchantOrderShipmentData,
    OrderShipmentStatus,
    TransportResponse,
)
from tests.unit.support import AUTH, BASE_URL, empty, json_response, only, setup

SHIPMENT: MerchantOrderShipmentData = {
    "channel": "API",
    "sender": {
        "fullname": "ร้านตัวอย่าง",
        "mobile_phone": "0811111111",
        "address": "1 ถนนสีลม",
        "sub_district": "สีลม",
        "district": "บางรัก",
        "province": "กรุงเทพมหานคร",
        "zip_code": "10500",
    },
    "recipient": {
        "fullname": "ลูกค้า",
        "mobile_phone": "0822222222",
        "address": "2 ถนนนิมมานเหมินท์",
        "sub_district": "สุเทพ",
        "district": "เมืองเชียงใหม่",
        "province": "เชียงใหม่",
        "zip_code": "50200",
    },
    "package": {
        "width": 10,
        "length": 20,
        "height": 5,
        "weight": 500,
        "my_tracking_no": "SHOP-1",
        "tracking_no": "TH0001",
        "ref1": "R1",
        "ref2": "",
        "ref3": "",
    },
    "status": "pending",
    "order_shipment_status": "Prepared",
    "created_at": "2026-10-06T03:00:00.000Z",
    "updated_at": None,
    "in_transit_at": None,
    "completed_at": None,
}

CREATE_REQUEST: MerchantOrderShipmentCreateRequest = {
    "shipping": {"shipment_provider_name": "Flash", "my_tracking_no": "SHOP-1"},
    "sender": {
        "fullname": "ร้านตัวอย่าง",
        "mobile_phone": "0811111111",
        "address": "1 ถนนสีลม",
        "sub_district": "สีลม",
        "district": "บางรัก",
        "province": "กรุงเทพมหานคร",
        "zip_code": "10500",
    },
    "recipient": {
        "fullname": "ลูกค้า",
        "mobile_phone": "0822222222",
        "address": "2 ถนนนิมมานเหมินท์",
        "sub_district": "สุเทพ",
        "district": "เมืองเชียงใหม่",
        "province": "เชียงใหม่",
        "zip_code": "50200",
    },
    "package": {
        "insurance_value": 0,
        "type": FlashArticleCategory.CLOTHES,
        "weight": 500,
        "width": 10,
        "height": 5,
        "length": 20,
    },
    "product_cods": [{"name": "เสื้อ", "amount": 2, "price_per_item": 150}],
}


def ok(data: object) -> TransportResponse:
    return json_response({"code": 200, "isSuccess": True, "message": "ok", "data": data}, 201)


def test_get_by_tracking_no_gets_get_by_tracking_no() -> None:
    client, transport = setup([json_response(SHIPMENT)])
    assert client.order_shipments.get_by_tracking_no("TH0001") == SHIPMENT
    call = only(transport)
    assert (call.method, call.url) == ("GET", f"{BASE_URL}/order-shipment/get-by-tracking-no/TH0001")
    assert call.headers["Authorization"] == AUTH


@pytest.mark.parametrize("response", [empty, lambda: json_response(None)], ids=["empty-body", "json-null"])
def test_get_by_tracking_no_returns_none_when_not_found(response: Callable[[], TransportResponse]) -> None:
    client, _ = setup([response()])
    assert client.order_shipments.get_by_tracking_no("NOPE") is None


def test_get_by_ref_gets_get_by_ref_and_none_when_not_found() -> None:
    client, transport = setup([json_response(SHIPMENT), empty()])
    assert client.order_shipments.get_by_ref("R1") == SHIPMENT
    assert client.order_shipments.get_by_ref("R404") is None
    assert [call.url for call in transport.calls] == [
        f"{BASE_URL}/order-shipment/get-by-ref/R1",
        f"{BASE_URL}/order-shipment/get-by-ref/R404",
    ]
    assert all(call.method == "GET" and call.headers["Authorization"] == AUTH for call in transport.calls)


def test_filter_posts_the_paging_body() -> None:
    page = {"count": 1, "limit": 20, "page": 1, "page_count": 1, "data": [SHIPMENT]}
    client, transport = setup([json_response(page, 201)])
    assert client.order_shipments.filter({"filter": "TH00", "page": 1, "limit": 20}) == page
    call = only(transport)
    assert (call.method, call.url) == ("POST", f"{BASE_URL}/order-shipment/filter")
    assert call.body == {"filter": "TH00", "page": 1, "limit": 20}
    assert call.headers["Content-Type"] == "application/json"
    assert call.headers["Authorization"] == AUTH


def test_create_posts_an_array_body_and_unwraps_data() -> None:
    client, transport = setup([ok([SHIPMENT])])
    assert client.order_shipments.create([CREATE_REQUEST]) == [SHIPMENT]
    call = only(transport)
    assert (call.method, call.url) == ("POST", f"{BASE_URL}/order-shipment/create")
    assert call.body == [CREATE_REQUEST]
    assert call.body[0]["package"]["type"] == 4
    assert call.headers["Content-Type"] == "application/json"
    assert call.headers["Authorization"] == AUTH


def test_create_wraps_a_single_request_into_the_array_the_server_expects() -> None:
    client, transport = setup([ok([SHIPMENT])])
    client.order_shipments.create(CREATE_REQUEST)
    assert only(transport).body == [CREATE_REQUEST]


def test_create_accepts_any_sequence() -> None:
    client, transport = setup([ok([SHIPMENT, SHIPMENT])])
    client.order_shipments.create((CREATE_REQUEST, CREATE_REQUEST))
    assert only(transport).body == [CREATE_REQUEST, CREATE_REQUEST]


def test_create_is_never_retried() -> None:
    client, transport = setup([json_response({"code": 500, "isSuccess": False, "message": "x", "data": None}, 500)])
    with pytest.raises(Exception):  # noqa: B017 - only the call count matters here
        client.order_shipments.create(CREATE_REQUEST)
    assert len(transport.calls) == 1


def test_calculate_price_posts_calculate_price() -> None:
    quote = {
        "price_infos": [
            {
                "description": "ค่าขนส่ง",
                "price": 35,
                "cost": 25,
                "cashback_cost": 0,
                "is_reward_cashback": False,
                "total_affliliate": 0,
            }
        ],
        "plan_detail": {"region": "UPC", "type": "weight", "min_boundary": 0, "max_boundary": 1000},
    }
    request: MerchantOrderShipmentCalculatePriceRequest = {
        "shipment_name": "Flash",
        "r_sub_district": "สุเทพ",
        "r_district": "เมืองเชียงใหม่",
        "r_province": "เชียงใหม่",
        "r_zip_code": "50200",
        "p_weight": 500,
        "p_width": 10,
        "p_height": 5,
        "p_length": 20,
        "p_cod": 300,
        "p_insurance": 0,
    }
    client, transport = setup([json_response(quote, 201)])
    assert client.order_shipments.calculate_price(request) == quote
    call = only(transport)
    assert (call.method, call.url, call.body) == ("POST", f"{BASE_URL}/order-shipment/calculate-price", request)
    assert call.headers["Content-Type"] == "application/json"
    assert call.headers["Authorization"] == AUTH


def test_cancel_posts_the_tracking_no() -> None:
    client, transport = setup([ok(None)])
    client.order_shipments.cancel("TH0001")
    call = only(transport)
    assert (call.method, call.url, call.body) == (
        "POST",
        f"{BASE_URL}/order-shipment/cancel",
        {"tracking_no": "TH0001"},
    )
    assert call.headers["Authorization"] == AUTH


def test_status_enums_compare_equal_to_wire_strings() -> None:
    client, _ = setup([json_response(SHIPMENT)])
    parcel = client.order_shipments.get_by_tracking_no("TH0001")
    assert parcel is not None
    assert parcel["order_shipment_status"] == OrderShipmentStatus.PREPARED
    wire: str = "In-Transit"
    assert wire == OrderShipmentStatus.IN_TRANSIT
