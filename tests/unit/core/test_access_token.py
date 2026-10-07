from __future__ import annotations

import base64
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest

from postway import AccessToken, AccessTokenRefreshReason, PostwayApiError, PostwayConfigError, TransportResponse
from tests.unit.support import BASE_URL, api_error, json_response, setup, text

T0 = datetime(2027, 1, 1, tzinfo=UTC)
ACCOUNT_INFO = f"{BASE_URL}/auth/account/info"
PROVIDERS = f"{BASE_URL}/shipment-provider/all"


class Clock:
    def __init__(self) -> None:
        self.now = T0

    def advance_to(self, seconds: float) -> None:
        self.now = T0 + timedelta(seconds=seconds)

    def __call__(self) -> float:
        return self.now.timestamp()


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    fake = Clock()
    monkeypatch.setattr("postway._access_token._now", fake)
    return fake


def jwt(issued_at: float, expires_at: float, subject: str = "shop") -> str:
    """Unsigned JWT with ``iat`` / ``exp`` as seconds after T0. Only the payload matters to the SDK."""

    def part(value: object) -> str:
        return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")

    base = T0.timestamp()
    return f"{part({'alg': 'none'})}.{part({'sub': subject, 'iat': base + issued_at, 'exp': base + expires_at})}.sig"


class Provider:
    """Hands out ``tokens`` in order and records why it was asked."""

    def __init__(self, *tokens: str | AccessToken) -> None:
        self.tokens = list(tokens)
        self.reasons: list[AccessTokenRefreshReason] = []

    def __call__(self, reason: AccessTokenRefreshReason) -> str | AccessToken:
        self.reasons.append(reason)
        if not self.tokens:
            raise AssertionError("no more tokens")
        return self.tokens.pop(0)


def bearer(token: str) -> str:
    return f"Bearer {token}"


def session(expires_in: float) -> TransportResponse:
    expired = (T0 + timedelta(seconds=expires_in)).isoformat().replace("+00:00", "Z")
    return json_response({"store": {}, "user": {}, "session": {"expired": expired}})


OK = json_response({"code": 200, "isSuccess": True, "message": "ok", "data": None})


def test_asks_the_provider_once_for_the_first_token_and_reuses_it_without_probing_a_jwt(clock: Clock) -> None:
    token = jwt(0, 100)
    provider = Provider(token)
    client, transport = setup([json_response([]), json_response([])], access_token=None, get_access_token=provider)
    client.shipment_providers.all()
    client.shipment_providers.all()
    assert provider.reasons == ["initial"]
    assert [c.url for c in transport.calls] == [PROVIDERS, PROVIDERS]
    assert [c.headers["Authorization"] for c in transport.calls] == [bearer(token), bearer(token)]


def test_refreshes_once_75_percent_of_the_jwt_lifetime_has_elapsed(clock: Clock) -> None:
    first, second = jwt(-10, 90), jwt(65, 165)
    provider = Provider(first, second)
    client, transport = setup([json_response([])] * 3, access_token=None, get_access_token=provider)

    client.shipment_providers.all()
    clock.advance_to(64.999)
    client.shipment_providers.all()
    clock.advance_to(65)
    client.shipment_providers.all()

    assert provider.reasons == ["initial", "expiring"]
    assert [c.headers["Authorization"] for c in transport.calls] == [bearer(first), bearer(first), bearer(second)]


def test_uses_the_expires_at_the_provider_returns_for_an_opaque_token_without_probing(clock: Clock) -> None:
    provider = Provider(
        AccessToken("opaque_1", T0 + timedelta(seconds=100)),
        AccessToken("opaque_2", "2027-01-01T00:03:20Z"),
    )
    client, transport = setup([json_response([])] * 2, access_token=None, get_access_token=provider)
    client.shipment_providers.all()
    clock.advance_to(75)
    client.shipment_providers.all()
    assert provider.reasons == ["initial", "expiring"]
    assert [c.headers["Authorization"] for c in transport.calls] == [bearer("opaque_1"), bearer("opaque_2")]


def test_probes_account_info_once_for_an_opaque_token_and_refreshes_at_75_percent_of_session_expired(
    clock: Clock,
) -> None:
    following = jwt(75, 175)
    provider = Provider(following)
    client, transport = setup(
        [session(100), json_response([]), json_response([]), json_response([])],
        access_token="opaque_static",
        get_access_token=provider,
    )

    client.shipment_providers.all()
    client.shipment_providers.all()
    assert [c.url for c in transport.calls] == [ACCOUNT_INFO, PROVIDERS, PROVIDERS]
    assert transport.calls[0].method == "POST"
    assert transport.calls[0].headers["Authorization"] == bearer("opaque_static")
    assert provider.reasons == []

    clock.advance_to(75)
    client.shipment_providers.all()
    assert provider.reasons == ["expiring"]
    assert transport.calls[3].headers["Authorization"] == bearer(following)


def test_learns_the_lifetime_from_the_callers_own_account_info_without_an_extra_probe(clock: Clock) -> None:
    following = jwt(75, 175)
    provider = Provider(following)
    client, transport = setup(
        [session(100), json_response([])], access_token="opaque_static", get_access_token=provider
    )
    client.auth.account_info()
    clock.advance_to(75)
    client.shipment_providers.all()
    assert len(transport.calls) == 2
    assert provider.reasons == ["expiring"]
    assert transport.calls[1].headers["Authorization"] == bearer(following)


def test_refreshes_straight_away_when_the_probe_gets_a_403(clock: Clock) -> None:
    following = jwt(0, 100)
    provider = Provider(following)
    client, transport = setup(
        [api_error(403, "Forbidden resource"), json_response([])],
        access_token="opaque_stale",
        get_access_token=provider,
    )
    client.shipment_providers.all()
    assert provider.reasons == ["forbidden"]
    assert [(c.url, c.headers["Authorization"]) for c in transport.calls] == [
        (ACCOUNT_INFO, bearer("opaque_stale")),
        (PROVIDERS, bearer(following)),
    ]


def test_carries_on_with_the_call_when_the_probe_fails_for_another_reason(clock: Clock) -> None:
    provider = Provider()
    client, transport = setup(
        [api_error(500, "Internal server error"), json_response([]), json_response([])],
        access_token="opaque_static",
        get_access_token=provider,
    )
    client.shipment_providers.all()
    client.shipment_providers.all()
    assert provider.reasons == []
    assert [c.url for c in transport.calls] == [ACCOUNT_INFO, PROVIDERS, PROVIDERS]


def test_403_refresh_replays_the_call_once_with_the_new_token_and_the_same_body(clock: Clock) -> None:
    first, second = jwt(0, 100, "first"), jwt(0, 100, "second")
    provider = Provider(first, second)
    client, transport = setup([api_error(403, "Forbidden resource"), OK], access_token=None, get_access_token=provider)

    client.order_shipments.cancel("PW1")

    assert provider.reasons == ["initial", "forbidden"]
    assert len(transport.calls) == 2
    assert [c.headers["Authorization"] for c in transport.calls] == [bearer(first), bearer(second)]
    assert (transport.calls[1].method, transport.calls[1].url) == (transport.calls[0].method, transport.calls[0].url)
    assert transport.calls[0].body == transport.calls[1].body == {"tracking_no": "PW1"}


def test_403_refresh_403_raises_without_a_third_request(clock: Clock) -> None:
    provider = Provider(jwt(0, 100, "a"), jwt(0, 100, "b"))
    client, transport = setup(
        [api_error(403, "Forbidden resource"), api_error(403, "Forbidden resource")],
        access_token=None,
        get_access_token=provider,
    )
    with pytest.raises(PostwayApiError) as error:
        client.shipment_providers.all()
    assert error.value.status == 403
    assert len(transport.calls) == 2
    assert provider.reasons == ["initial", "forbidden"]


def test_does_not_replay_after_a_403_when_the_probe_already_used_the_refresh(clock: Clock) -> None:
    provider = Provider("opaque_new")
    client, transport = setup(
        [api_error(403, "Forbidden resource"), api_error(403, "Forbidden resource")],
        access_token="opaque_stale",
        get_access_token=provider,
    )
    with pytest.raises(PostwayApiError):
        client.shipment_providers.all()
    assert provider.reasons == ["forbidden"]
    assert len(transport.calls) == 2


def test_without_a_provider_neither_probes_refreshes_nor_replays() -> None:
    client, transport = setup([api_error(403, "Forbidden resource")], access_token="opaque_static")
    with pytest.raises(PostwayApiError):
        client.shipment_providers.all()
    assert len(transport.calls) == 1


def test_never_probes_refreshes_authenticates_or_replays_public_routes(clock: Clock) -> None:
    provider = Provider()
    client, transport = setup(
        [text("pong"), api_error(403, "Forbidden resource")], access_token=None, get_access_token=provider
    )
    client.health.ping()
    with pytest.raises(PostwayApiError):
        client.receipts.get_public("rcpt")
    assert provider.reasons == []
    assert len(transport.calls) == 2
    assert all("Authorization" not in c.headers for c in transport.calls)


def test_shares_one_provider_call_and_one_probe_between_concurrent_calls(clock: Clock) -> None:
    called = threading.Event()
    release = threading.Event()
    reasons: list[AccessTokenRefreshReason] = []

    def provider(reason: AccessTokenRefreshReason) -> str:
        reasons.append(reason)
        called.set()
        assert release.wait(5)
        return "opaque_1"

    client, transport = setup(
        [session(100), json_response([]), json_response([]), json_response([])],
        access_token=None,
        get_access_token=provider,
    )
    with ThreadPoolExecutor(3) as pool:
        futures = [pool.submit(client.shipment_providers.all) for _ in range(3)]
        assert called.wait(5)
        release.set()
        for future in futures:
            future.result()

    assert reasons == ["initial"]
    assert [c.url for c in transport.calls].count(ACCOUNT_INFO) == 1
    assert len(transport.calls) == 4


def test_rejects_an_unsafe_token_from_the_provider_without_echoing_it_before_any_request(clock: Clock) -> None:
    client, transport = setup([], access_token=None, get_access_token=Provider("secret\r\nX-Injected: 1"))
    with pytest.raises(PostwayConfigError) as error:
        client.shipment_providers.all()
    assert "secret" not in str(error.value)
    assert transport.calls == []


def test_rejects_an_invalid_expires_at_from_the_provider(clock: Clock) -> None:
    client, transport = setup([], access_token=None, get_access_token=Provider(AccessToken("opaque", "not a date")))
    with pytest.raises(PostwayConfigError):
        client.shipment_providers.all()
    assert transport.calls == []


def test_propagates_a_provider_error_unchanged_and_sends_nothing() -> None:
    failure = RuntimeError("login service down")

    def provider(reason: AccessTokenRefreshReason) -> str:
        raise failure

    client, transport = setup([], access_token=None, get_access_token=provider)
    with pytest.raises(RuntimeError) as error:
        client.shipment_providers.all()
    assert error.value is failure
    assert transport.calls == []


def test_rejects_a_non_callable_get_access_token() -> None:
    with pytest.raises(PostwayConfigError, match=r"^get_access_token must be callable$"):
        setup(get_access_token="token")


def test_access_token_repr_hides_the_token() -> None:
    assert "secret" not in repr(AccessToken("secret", T0))
