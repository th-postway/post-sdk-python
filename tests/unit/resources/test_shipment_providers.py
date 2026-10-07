from __future__ import annotations

from typing import Any

from tests.unit.support import AUTH, BASE_URL, json_response, only, setup


def test_all_gets_shipment_provider_all() -> None:
    providers: list[Any] = [{"name": "Flash", "display_name": "Flash Express"}]
    client, transport = setup([json_response(providers)])
    assert client.shipment_providers.all() == providers
    call = only(transport)
    assert (call.method, call.url) == ("GET", f"{BASE_URL}/shipment-provider/all")
    assert call.headers["Authorization"] == AUTH
