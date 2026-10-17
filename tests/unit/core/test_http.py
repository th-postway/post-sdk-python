from __future__ import annotations

import json
import pickle
import urllib.error
from collections.abc import Callable
from typing import Any

import pytest

from postway import (
    PostwayApiError,
    PostwayBusinessError,
    PostwayConfigError,
    PostwayMerchantClient,
    PostwayRequestError,
    TransportRequest,
    TransportResponse,
)
from tests.unit.support import (
    BASE_URL,
    TOKEN,
    FakeTransport,
    api_error,
    empty,
    json_response,
    no_body,
    only,
    setup,
    text,
)


def test_encodes_path_parameters() -> None:
    client, transport = setup([json_response(None)])
    client.order_shipments.get_by_ref("A/B ?#1")
    assert only(transport).url == f"{BASE_URL}/order-shipment/get-by-ref/A%2FB%20%3F%231"


@pytest.mark.parametrize("value", ["\ud800", "a\udc00"], ids=["lone-high", "lone-low"])
def test_rejects_a_lone_surrogate_in_a_path_parameter_before_any_request(value: str) -> None:
    client, transport = setup()
    with pytest.raises(PostwayConfigError) as caught:
        client.order_shipments.get_by_ref(value)
    assert str(caught.value) == "ref must be well-formed Unicode text"
    assert transport.calls == []


def test_encodes_a_non_bmp_character_in_a_path_parameter() -> None:
    client, transport = setup([json_response(None)])
    client.order_shipments.get_by_ref("A😀")
    assert only(transport).url == f"{BASE_URL}/order-shipment/get-by-ref/A%F0%9F%98%80"


def test_keeps_dots_inside_a_path_parameter() -> None:
    client, transport = setup([json_response({})], access_token=None)
    client.receipts.get_public("abc.def")
    assert only(transport).url == f"{BASE_URL}/receipt/public/abc.def"


@pytest.mark.parametrize("value", ["", ".", ".."], ids=["empty", "dot", "dotdot"])
def test_rejects_unsafe_path_parameters_before_any_request(value: str) -> None:
    client, transport = setup()
    calls: list[Callable[[], object]] = [
        lambda: client.order_shipments.get_by_ref(value),
        lambda: client.order_shipments.get_by_tracking_no(value),
        lambda: client.labels.receipt(value),
        lambda: client.receipts.get_public(value),
        lambda: client.receipts.get_public_html(value),
    ]
    for call in calls:
        with pytest.raises(PostwayConfigError):
            call()
    assert transport.calls == []


def test_public_url_rejects_dotdot() -> None:
    client, _ = setup()
    with pytest.raises(PostwayConfigError):
        client.receipts.public_url("..")


def test_sets_content_type_only_when_there_is_a_body() -> None:
    client, transport = setup([json_response({}), json_response([])])
    client.auth.account_info()
    client.shipment_providers.all()
    assert "Content-Type" not in transport.calls[0].headers
    assert transport.calls[0].body is no_body()
    assert "Content-Type" not in transport.calls[1].headers


def test_sends_the_accept_header() -> None:
    client, transport = setup([text("pong")])
    client.health.ping()
    assert only(transport).headers["Accept"] == "application/json, text/plain;q=0.9, */*;q=0.8"


def test_refuses_a_redirect_response() -> None:
    client, transport = setup([TransportResponse(302, {"Location": "https://elsewhere.test/"}, b"")])
    with pytest.raises(PostwayRequestError) as caught:
        client.auth.account_info()
    assert caught.value.url == f"{BASE_URL}/auth/account/info"
    assert str(caught.value) == f"POST {BASE_URL}/auth/account/info failed: redirect refused"
    assert len(transport.calls) == 1


def test_keeps_the_token_and_body_out_of_the_transport_request_repr() -> None:
    seen: list[TransportRequest] = []

    class Recording:
        def send(self, request: TransportRequest) -> TransportResponse:
            seen.append(request)
            return empty()

    client = PostwayMerchantClient(base_url=BASE_URL, access_token=TOKEN, transport=Recording())
    client.order_shipments.filter({"page": 1, "limit": 1, "filter": "recipient-secret"})
    shown = repr(seen[0])
    assert shown.startswith("TransportRequest(method='POST'")
    assert TOKEN not in shown
    assert "recipient-secret" not in shown


def test_refuses_a_guarded_call_without_an_access_token_before_any_request() -> None:
    client, transport = setup([], access_token=None)
    with pytest.raises(PostwayConfigError, match=r"^POST auth/account/info requires a merchant access token"):
        client.auth.account_info()
    assert transport.calls == []


@pytest.mark.parametrize(
    ("status", "message", "code"),
    [
        (400, "ไม่พบคำสั่งซื้อ", 400),
        (403, "Forbidden resource", 400),
        (404, "not found", 400),
        (500, "เกิดข้อผิดพลาดในระบบ", 500),
    ],
)
def test_maps_http_errors_to_api_error(status: int, message: str, code: int) -> None:
    client, _ = setup([api_error(status, message)])
    with pytest.raises(PostwayApiError) as caught:
        client.shipment_providers.all()
    error = caught.value
    assert not isinstance(error, PostwayBusinessError)
    assert (error.status, error.code, error.messages, str(error), error.method, error.url) == (
        status,
        code,
        [message],
        message,
        "GET",
        f"{BASE_URL}/shipment-provider/all",
    )


def test_keeps_every_validation_message() -> None:
    client, _ = setup([api_error(400, ["limit must not be less than 1", "page should not be empty"])])
    with pytest.raises(PostwayApiError) as caught:
        client.order_shipments.filter({"page": 0, "limit": 0})
    assert caught.value.messages == ["limit must not be less than 1", "page should not be empty"]
    assert str(caught.value) == "limit must not be less than 1; page should not be empty"


def test_falls_back_to_the_status_when_there_is_no_message() -> None:
    client, _ = setup([TransportResponse(503)])
    with pytest.raises(PostwayApiError, match=r"^HTTP 503$"):
        client.shipment_providers.all()


def test_handles_a_non_json_error_body() -> None:
    client, _ = setup([text("<html>Bad Gateway</html>", 502)])
    with pytest.raises(PostwayApiError) as caught:
        client.shipment_providers.all()
    assert caught.value.status == 502
    assert caught.value.body == "<html>Bad Gateway</html>"
    assert caught.value.code is None
    assert caught.value.messages == []
    assert str(caught.value) == "HTTP 502"


def test_keeps_a_text_error_body_that_echoes_the_path_out_of_the_message() -> None:
    echoed = "Cannot GET /merchant/receipt/public/secret-token"
    client, _ = setup([text(echoed, 404, "text/plain")], access_token=None)
    with pytest.raises(PostwayApiError) as caught:
        client.receipts.get_public("secret-token")
    assert str(caught.value) == "HTTP 404"
    assert caught.value.body == echoed
    assert "secret-token" not in repr(caught.value)


def test_keeps_malformed_json_as_text() -> None:
    client, _ = setup([TransportResponse(200, {"content-type": "application/json"}, b"{not json")])
    assert client.receipts.get_public_html("tok") == "{not json"


def test_keeps_the_response_body_readable_but_out_of_str_repr_vars_and_pickles() -> None:
    body = {"code": 400, "isSuccess": False, "message": "ไม่พบคำสั่งซื้อ", "data": None, "trace": "internal-detail"}
    client, _ = setup([json_response(body, 400)])
    with pytest.raises(PostwayApiError) as caught:
        client.shipment_providers.all()
    error = caught.value
    assert error.body == body
    assert "body" not in vars(error)
    assert "_body" not in vars(error)
    for rendered in (str(error), repr(error), repr(error.args), json.dumps(vars(error), ensure_ascii=False)):
        assert "internal-detail" not in rendered
    restored = pickle.loads(pickle.dumps(error))  # noqa: S301 - round-tripping our own object
    assert isinstance(restored, PostwayApiError)
    assert (restored.status, restored.messages, restored.url) == (400, ["ไม่พบคำสั่งซื้อ"], error.url)
    assert restored.body is None


def test_reports_the_route_template_instead_of_the_receipt_token() -> None:
    client, _ = setup([api_error(404, "ไม่พบใบเสร็จ")], access_token=None)
    with pytest.raises(PostwayApiError) as caught:
        client.receipts.get_public("secret-token")
    assert caught.value.url == f"{BASE_URL}/receipt/public/:token"
    assert "secret-token" not in str(caught.value)
    assert "secret-token" not in repr(caught.value)
    assert "secret-token" not in json.dumps(vars(caught.value))


def test_reports_the_route_template_for_tracking_number_lookups() -> None:
    client, _ = setup([api_error(400, "ไม่พบคำสั่งซื้อ")])
    with pytest.raises(PostwayApiError) as caught:
        client.order_shipments.get_by_tracking_no("TH0001")
    assert caught.value.url == f"{BASE_URL}/order-shipment/get-by-tracking-no/:tracking_no"
    assert "TH0001" not in json.dumps(vars(caught.value), ensure_ascii=False)
    assert "TH0001" not in repr(caught.value)


def test_turns_a_2xx_envelope_with_is_success_false_into_business_error() -> None:
    client, _ = setup([json_response({"code": 400, "isSuccess": False, "message": "ยอดเงินไม่พอ", "data": None}, 201)])
    with pytest.raises(PostwayBusinessError) as caught:
        client.order_shipments.cancel("TH1")
    assert (caught.value.status, caught.value.code, caught.value.messages) == (201, 400, ["ยอดเงินไม่พอ"])


def test_rejects_a_2xx_response_that_is_not_an_envelope_where_one_is_expected() -> None:
    client, _ = setup([json_response([1, 2])])
    with pytest.raises(PostwayApiError, match=r"expected \{ code, isSuccess"):
        client.order_shipments.cancel("TH1")


def test_wraps_network_failures_with_the_cause_and_a_redacted_url() -> None:
    cause = urllib.error.URLError(ConnectionRefusedError(61, "Connection refused"))
    client = PostwayMerchantClient(base_url=BASE_URL, transport=FakeTransport([cause]))
    with pytest.raises(PostwayRequestError) as caught:
        client.receipts.get_public("secret-token")
    error = caught.value
    assert error.__cause__ is cause
    assert error.url == f"{BASE_URL}/receipt/public/:token"
    assert str(error) == f"GET {BASE_URL}/receipt/public/:token failed: [Errno 61] Connection refused"
    assert "secret-token" not in str(error)


@pytest.mark.parametrize(
    "reason",
    [
        f"request to {BASE_URL}/receipt/public/secret-token failed, reason: ECONNREFUSED",
        "Max retries exceeded with url: /merchant/receipt/public/secret-token",
    ],
    ids=["full-url", "path-only"],
)
def test_redacts_the_url_quoted_by_a_transport_exception(reason: str) -> None:
    cause = RuntimeError(reason)
    client = PostwayMerchantClient(base_url=BASE_URL, transport=FakeTransport([cause]))
    with pytest.raises(PostwayRequestError) as caught:
        client.receipts.get_public("secret-token")
    assert "secret-token" not in str(caught.value)
    assert "/merchant/receipt/public/:token" in str(caught.value)
    assert caught.value.__cause__ is cause


def test_redacts_the_access_token_quoted_by_a_transport_exception() -> None:
    client = PostwayMerchantClient(
        base_url=BASE_URL, access_token=TOKEN, transport=FakeTransport([RuntimeError(f"bad header Bearer {TOKEN}")])
    )
    with pytest.raises(PostwayRequestError) as caught:
        client.order_shipments.get_by_tracking_no("TH0001")
    assert str(caught.value) == (
        f"GET {BASE_URL}/order-shipment/get-by-tracking-no/:tracking_no failed: bad header Bearer [redacted]"
    )


def test_wraps_any_transport_exception() -> None:
    cause = RuntimeError("boom")
    client = PostwayMerchantClient(base_url=BASE_URL, transport=FakeTransport([cause]))
    with pytest.raises(PostwayRequestError, match=r"failed: boom$") as caught:
        client.health.ping()
    assert caught.value.__cause__ is cause


@pytest.mark.parametrize(
    "cause", [TimeoutError("timed out"), urllib.error.URLError(TimeoutError("timed out"))], ids=["read", "connect"]
)
def test_times_out_with_request_error_and_a_redacted_url(cause: BaseException) -> None:
    client = PostwayMerchantClient(base_url=BASE_URL, timeout=0.02, transport=FakeTransport([cause]))
    with pytest.raises(PostwayRequestError) as caught:
        client.receipts.get_public("secret-token")
    assert str(caught.value) == f"GET {BASE_URL}/receipt/public/:token timed out after 0.02 s"
    assert caught.value.__cause__ is cause


def test_passes_the_client_and_per_call_timeouts_to_the_transport() -> None:
    client, transport = setup([text("pong"), text("pong")], timeout=5)
    client.health.ping()
    client.health.ping(timeout=0.5)
    assert [call.timeout for call in transport.calls] == [5.0, 0.5]


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), True, "60"])
def test_rejects_a_bad_per_call_timeout_before_any_request(timeout: Any) -> None:
    client, transport = setup()
    with pytest.raises(PostwayConfigError, match=r"^timeout must be a positive number of seconds"):
        client.health.ping(timeout=timeout)
    assert transport.calls == []


def test_decodes_the_body_with_the_declared_charset() -> None:
    client, _ = setup([TransportResponse(200, {"Content-Type": "text/plain; charset=tis-620"}, "พง".encode("tis-620"))])
    assert client.health.ping() == "พง"


def test_empty_query_values_are_dropped() -> None:
    client, transport = setup([json_response({})])
    client.labels.receipt("RC-1", receipt_size="")
    assert only(transport).url == f"{BASE_URL}/label/receipt/RC-1"
