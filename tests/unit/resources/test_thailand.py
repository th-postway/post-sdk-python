from __future__ import annotations

from tests.unit.support import AUTH, BASE_URL, json_response, setup


def test_filter_posts_thailand_filter_and_always_sends_shipment_provider_names() -> None:
    page = {"count": 0, "limit": 10, "page": 1, "page_count": 0, "data": []}
    client, transport = setup([json_response(page, 201), json_response(page, 201)])
    assert client.thailand.filter({"page": 1, "limit": 10, "zip_code": "50200"}) == page
    client.thailand.filter({"page": 1, "limit": 10, "shipment_provider_names": ["Flash"]})
    first, second = transport.calls
    assert (first.method, first.url) == ("POST", f"{BASE_URL}/thailand/filter")
    assert first.body == {"page": 1, "limit": 10, "zip_code": "50200", "shipment_provider_names": []}
    assert first.headers["Content-Type"] == "application/json"
    assert first.headers["Authorization"] == AUTH
    assert second.body["shipment_provider_names"] == ["Flash"]
