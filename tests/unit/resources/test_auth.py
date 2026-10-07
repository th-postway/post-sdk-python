from __future__ import annotations

from tests.unit.support import AUTH, BASE_URL, json_response, no_body, only, setup


def test_account_info_posts_with_the_bearer_token_and_no_body() -> None:
    info = {
        "store": {"code": "S1", "name": "Shop"},
        "user": {"username": "owner"},
        "session": {"expired": "2027-01-01T00:00:00.000Z"},
    }
    client, transport = setup([json_response(info, 201)])
    assert client.auth.account_info() == info
    call = only(transport)
    assert (call.method, call.url, call.body) == ("POST", f"{BASE_URL}/auth/account/info", no_body())
    assert call.headers["Authorization"] == AUTH
