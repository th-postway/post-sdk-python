from __future__ import annotations

import re
from typing import Any

import pytest

from postway import MERCHANT_BASE_URLS, PostwayConfigError, PostwayMerchantClient
from tests.unit.support import FakeTransport, json_response, only, setup


def config_error(**options: Any) -> PostwayConfigError:
    """Construct with ``options`` and return the ``PostwayConfigError`` it raises."""
    options.setdefault("transport", FakeTransport())
    with pytest.raises(PostwayConfigError) as caught:
        PostwayMerchantClient(**options)
    return caught.value


def test_defaults_to_the_production_base_url() -> None:
    assert PostwayMerchantClient(transport=FakeTransport()).base_url == "https://post.postway.co.th/merchant"


@pytest.mark.parametrize(("environment", "url"), list(MERCHANT_BASE_URLS.items()))
def test_resolves_environment(environment: Any, url: str) -> None:
    assert PostwayMerchantClient(environment=environment, transport=FakeTransport()).base_url == url


def test_only_production_and_sandbox_are_built_in() -> None:
    assert dict(MERCHANT_BASE_URLS) == {
        "production": "https://post.postway.co.th/merchant",
        "sandbox": "https://sandbox-post.postway.co.th/merchant",
    }
    with pytest.raises(TypeError):
        MERCHANT_BASE_URLS["qa"] = "https://qa.example"  # type: ignore[index]


def test_an_explicit_base_url_wins_over_environment() -> None:
    client = PostwayMerchantClient(
        base_url="https://merchant.example/v1", environment="sandbox", transport=FakeTransport()
    )
    assert client.base_url == "https://merchant.example/v1"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("http://localhost:3000/api//", "http://localhost:3000/api"),
        ("http://127.0.0.1:3000/api", "http://127.0.0.1:3000/api"),
        ("http://[::1]:3000/api", "http://[::1]:3000/api"),
        ("HTTPS://Merchant.Example/merchant/", "https://merchant.example/merchant"),
        ("https://merchant.example", "https://merchant.example"),
        ("https://merchant.example:443/merchant", "https://merchant.example/merchant"),
        ("https://merchant.example:8443/merchant", "https://merchant.example:8443/merchant"),
    ],
)
def test_accepts_and_normalises_base_url(raw: str, expected: str) -> None:
    assert PostwayMerchantClient(base_url=raw, transport=FakeTransport()).base_url == expected


@pytest.mark.parametrize(
    ("base_url", "secret"),
    [
        ("http://merchant.example/merchant", "merchant.example"),
        ("ftp://merchant.example/merchant", "ftp:"),
        ("file:///etc/passwd", "passwd"),
        ("/merchant", "/merchant"),
        ("not a url", "not a url"),
        ("https://user:s3cret@merchant.example/merchant", "s3cret"),
        ("https://merchant.example/merchant?debug=1", "debug"),
        ("https://merchant.example/merchant?", "merchant.example"),
        ("https://merchant.example/merchant#section-9", "section-9"),
        ("https://merchant.example:99999/merchant", "99999"),
        ("https://merchant.example\r\n/merchant", "merchant.example"),
        ("https://bad_host!/merchant", "bad_host"),
    ],
    ids=[
        "plain-http-remote",
        "ftp",
        "file",
        "relative",
        "non-url",
        "credentials",
        "query",
        "bare-question-mark",
        "fragment",
        "bad-port",
        "control-chars",
        "bad-host",
    ],
)
def test_rejects_unsafe_base_url_without_echoing_it(base_url: str, secret: str) -> None:
    assert secret not in str(config_error(base_url=base_url))


def test_rejects_an_unknown_environment_naming_the_valid_ones_but_not_the_input() -> None:
    error = config_error(environment="qa")
    assert "production, sandbox" in str(error)
    assert "qa" not in str(error)


@pytest.mark.parametrize(
    ("options", "secret"),
    [
        ({"access_token": "tok\r\nX-Injected: 1"}, "X-Injected"),
        ({"access_token": "secret-tok\n"}, "secret-tok"),
        ({"token_type": "Bearer\n"}, "Bearer\n"),
        ({"token_type": "Bearer x"}, "Bearer x"),
        ({"user_agent": "ua\x00"}, "ua\x00"),
        ({"user_agent": "ร้าน/1.0"}, "ร้าน"),
        ({"user_agent": ""}, "None"),
    ],
    ids=["token-crlf", "token-trailing-newline", "type-newline", "type-space", "ua-nul", "ua-non-ascii", "ua-empty"],
)
def test_rejects_header_injection_at_construction(options: dict[str, Any], secret: str) -> None:
    assert secret not in str(config_error(**options))


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), 2_147_484, True, "60000", None])
def test_rejects_bad_timeouts(timeout: Any) -> None:
    error = config_error(timeout=timeout)
    assert re.match(r"^timeout must be a positive number of seconds", str(error))
    assert "60000" not in str(error)


def test_requires_the_transport_to_have_send() -> None:
    config_error(transport=object())


def test_uses_the_configured_token_type_and_user_agent() -> None:
    client, transport = setup([json_response({})], token_type="Custom", user_agent="my-shop/1.0")
    client.auth.account_info()
    headers = only(transport).headers
    assert headers["Authorization"] == "Custom tok_123"
    assert headers["User-Agent"] == "my-shop/1.0"


def test_sends_a_default_user_agent_naming_the_sdk_and_python_versions() -> None:
    client, transport = setup([json_response({})])
    client.auth.account_info()
    assert re.match(r"^postway-sdk-python/\d+\.\d+\.\d+ python/\d+\.\d+", only(transport).headers["User-Agent"])


def test_an_empty_access_token_counts_as_none() -> None:
    client, transport = setup([], access_token="")
    with pytest.raises(PostwayConfigError, match="requires a merchant access token"):
        client.auth.account_info()
    assert transport.calls == []


def test_close_and_context_manager_close_the_transport() -> None:
    transport = FakeTransport()
    with PostwayMerchantClient(transport=transport) as client:
        assert client.base_url
    assert transport.closed


def test_repr_never_shows_the_token() -> None:
    client, _ = setup()
    assert "tok_123" not in repr(client)
    assert "tok_123" not in repr(vars(client))
