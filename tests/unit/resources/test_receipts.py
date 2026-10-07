from __future__ import annotations

import pytest

from postway import PostwayApiError
from tests.unit.support import BASE_URL, json_response, only, setup, text


def test_get_public_gets_receipt_public_token_without_authorization() -> None:
    receipt = {"is_available": True, "no": "RC-001", "shipments": []}
    client, transport = setup([json_response(receipt)], access_token=None)
    assert client.receipts.get_public("abc.def") == receipt
    call = only(transport)
    assert (call.method, call.url) == ("GET", f"{BASE_URL}/receipt/public/abc.def")
    assert "Authorization" not in call.headers


def test_get_public_never_sends_the_token_even_when_the_client_has_one() -> None:
    client, transport = setup([json_response({})])
    client.receipts.get_public("abc")
    assert "Authorization" not in only(transport).headers


def test_get_public_raises_api_error_404_for_a_bad_token() -> None:
    client, _ = setup([json_response({"code": 400, "isSuccess": False, "message": "ไม่พบใบเสร็จ", "data": None}, 404)])
    with pytest.raises(PostwayApiError) as caught:
        client.receipts.get_public("bad")
    assert caught.value.status == 404


def test_get_public_html_returns_text_and_a_404_page_becomes_api_error_with_the_html_body() -> None:
    client, transport = setup([text("<html>ok</html>"), text("<html>ไม่พบ</html>", 404)])
    assert client.receipts.get_public_html("tok") == "<html>ok</html>"
    with pytest.raises(PostwayApiError) as caught:
        client.receipts.get_public_html("bad")
    assert caught.value.body == "<html>ไม่พบ</html>"
    assert transport.calls[0].url == f"{BASE_URL}/receipt/tok"
    assert transport.calls[0].method == "GET"
    assert "Authorization" not in transport.calls[0].headers


def test_public_url_builds_the_qr_link_without_a_request() -> None:
    client, transport = setup()
    assert client.receipts.public_url("a/b") == f"{BASE_URL}/receipt/a%2Fb"
    assert transport.calls == []
