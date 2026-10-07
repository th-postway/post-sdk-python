from __future__ import annotations

from tests.unit.support import BASE_URL, empty, json_response, only, setup, text


def test_ping_gets_health_ping_without_authorization() -> None:
    client, transport = setup([text("pong")])
    assert client.health.ping() == "pong"
    call = only(transport)
    assert (call.method, call.url) == ("GET", f"{BASE_URL}/health/ping")
    assert "Authorization" not in call.headers


def test_ping_stringifies_json_and_empty_bodies() -> None:
    client, _ = setup([json_response({"status": "ok"}), empty()], access_token=None)
    assert client.health.ping() == '{"status":"ok"}'
    assert client.health.ping() == ""
