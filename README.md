# th-postway-post-sdk

Python SDK for the **Postway Merchant API**: create and track parcels, quote prices, print labels and receipts, and look up Thai postal areas. It covers every live Merchant endpoint, has **zero runtime dependencies** (standard-library `urllib`), and ships inline type hints (`py.typed`).

It is a port of the Node SDK [`@th-postway/post-sdk`](https://github.com/th-postway/post-sdk-node), with the same endpoints, wire fields, environments, error semantics and security rules. See [Mapping from the Node SDK](#mapping-from-the-node-sdk).

- [Requirements](#requirements)
- [Install](#install)
- [Quick start](#quick-start)
- [Authentication](#authentication)
- [Environments](#environments)
- [Method catalogue](#method-catalogue)
- [Errors](#errors)
- [Labels and receipt files](#labels-and-receipt-files)
- [Security](#security)
- [Units and conventions](#units-and-conventions)
- [Development](#development)
- [Mapping from the Node SDK](#mapping-from-the-node-sdk)

## Requirements

**Python ≥ 3.11.** No third-party packages are needed at runtime.

## Install

```bash
pip install th-postway-post-sdk
# or
uv add th-postway-post-sdk
```

The import name is `postway`.

## Quick start

```python
import os
from pathlib import Path

from postway import LabelOrientation, LabelSize, PostwayMerchantClient, decode_file

client = PostwayMerchantClient(
    access_token=os.environ["POSTWAY_ACCESS_TOKEN"],  # never hardcode it
    environment="production",  # default
)

account = client.auth.account_info()
print(account["store"]["name"], "token expires", account["session"]["expired"])

[parcel] = client.order_shipments.create(
    {
        "shipping": {"shipment_provider_name": "Flash", "my_tracking_no": "ORDER-1001"},
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

label = client.labels.order_shipments(
    {
        "tracking_nos": [parcel["package"]["tracking_no"]],
        "label_size": LabelSize.SIZE_4X6,
        "label_orientation": LabelOrientation.PORTRAIT,
    }
)
# Path(...).name keeps a server-supplied name from escaping the current directory.
Path(Path(label["file_name"]).name).write_bytes(decode_file(label))
```

Requests and responses are plain `dict`s typed as `TypedDict`s, so editors and type checkers (mypy, pyright) know every key, and fields the SDK does not know yet still come through.

## Authentication

The Merchant API uses a **merchant session access token**. Postway issues it to your store out of band; there is no token endpoint in the API. The SDK sends it as:

```
Authorization: Bearer <access_token>
```

- The server looks up the session by token type plus token, so pass `token_type` only if Postway gave you a different type. The default is `"Bearer"`.
- Every call acts as the **owner of the store** the token belongs to, and every query is scoped to that store.
- A missing, unknown or **expired** token gets HTTP **403**. `auth.account_info()` returns `session.expired`, so you can rotate the token before it expires.
- `receipts.*` and `health.ping()` are public and never send the token. Every other method raises `PostwayConfigError` before any network call if the client has no `access_token`.

## Environments

| `environment`            | Base URL                                      |
| ------------------------ | --------------------------------------------- |
| `production` _(default)_ | `https://post.postway.co.th/merchant`         |
| `sandbox`                | `https://sandbox-post.postway.co.th/merchant` |

`base_url` overrides `environment`:

```python
PostwayMerchantClient(base_url="https://sandbox-post.postway.co.th/merchant", access_token=token)
```

### Client options

All options are keyword-only.

| Option         | Default                                  | Notes                                                                        |
| -------------- | ---------------------------------------- | ---------------------------------------------------------------------------- |
| `access_token` | —                                        | Merchant session token                                                       |
| `token_type`   | `"Bearer"`                               | Auth scheme word of `Authorization`                                          |
| `environment`  | `"production"`                           | See table above                                                              |
| `base_url`     | from `environment`                       | `https://` only (`http://` for localhost); no credentials, query or fragment |
| `timeout`      | `60.0`                                   | Seconds, per request; override per call with `timeout=`                      |
| `transport`    | `UrllibTransport()`                      | Inject for proxies, tracing or tests (see below)                             |
| `user_agent`   | `postway-sdk-python/<ver> python/<ver>`  |                                                                              |

Every method takes a keyword-only `timeout: float | None` that overrides the client's for that call.

The constructor validates every option and raises `PostwayConfigError` for unsafe values. Its messages never repeat the value, so they are safe to log.

The client can be used as a context manager (`with PostwayMerchantClient(...) as client:`); `close()` is forwarded to the transport.

### Custom transport

A transport is any object with `send(request: TransportRequest) -> TransportResponse`:

```python
from postway import PostwayMerchantClient, TransportRequest, TransportResponse


class MyTransport:
    def send(self, request: TransportRequest) -> TransportResponse:
        # request.method, request.url, request.headers, request.body (bytes | None), request.timeout (s)
        ...
        return TransportResponse(status=200, headers={"Content-Type": "application/json"}, body=b"{}")
```

A transport must **not follow redirects**, must return 4xx/5xx as responses rather than raising, and should raise `TimeoutError` on timeout. Any other exception it raises becomes `PostwayRequestError`; a 3xx response is refused the same way.

The default `UrllibTransport(ssl_context=None)` uses `ssl.create_default_context()` unless you pass a context, and keeps urllib's standard proxy handling.

## Method catalogue

Paths are relative to the base URL.

| Method                                                                         | HTTP                                                 | Auth | Returns                                                               |
| ------------------------------------------------------------------------------ | ---------------------------------------------------- | ---- | --------------------------------------------------------------------- |
| `auth.account_info()`                                                          | `POST auth/account/info`                             | ✓    | `MerchantAuthAccountInfoResponse`: store, owner, `session.expired`    |
| `order_shipments.get_by_tracking_no(tracking_no)`                              | `GET order-shipment/get-by-tracking-no/:tracking_no` | ✓    | `MerchantOrderShipmentData \| None`                                   |
| `order_shipments.get_by_ref(ref)`                                              | `GET order-shipment/get-by-ref/:ref`                 | ✓    | `MerchantOrderShipmentData \| None`; matches `ref1`, `ref2` or `ref3` |
| `order_shipments.filter({"filter"?, "page", "limit"})`                         | `POST order-shipment/filter`                         | ✓    | `FilterResponse[MerchantOrderShipmentData]`, newest first             |
| `order_shipments.create(request \| [request, ...])`                            | `POST order-shipment/create`                         | ✓    | `list[MerchantOrderShipmentData]`                                     |
| `order_shipments.calculate_price(request)`                                     | `POST order-shipment/calculate-price`                | ✓    | `{"price_infos", "plan_detail"}`                                      |
| `order_shipments.cancel(tracking_no)`                                          | `POST order-shipment/cancel`                         | ✓    | `None`                                                                |
| `shipment_providers.all()`                                                     | `GET shipment-provider/all`                          | ✓    | `list[MerchantShipmentProviderData]`: couriers this store may use     |
| `thailand.filter({"page", "limit", ...})`                                      | `POST thailand/filter`                               | ✓    | `FilterResponse[MerchantThailand]`                                    |
| `labels.order_shipments({"tracking_nos", "label_size", "label_orientation"})`  | `POST label/order/shipments`                         | ✓    | `FileHttpResponse` (base64)                                           |
| `labels.receipt(receipt_no, *, receipt_size=None)`                             | `GET label/receipt/:receipt_no?receipt_size=`        | ✓    | `FileHttpResponse` (base64)                                           |
| `receipts.get_public(token)`                                                   | `GET receipt/public/:token`                          | —    | `PublicReceiptResponse`                                               |
| `receipts.get_public_html(token)`                                              | `GET receipt/:token`                                 | —    | HTML `str`                                                            |
| `receipts.public_url(token)`                                                   | _(no request)_                                       | —    | URL of the public receipt page                                        |
| `health.ping()`                                                                | `GET health/ping`                                    | —    | `"pong"`                                                              |

Behaviour worth knowing:

- **`order_shipments.create`** accepts one request or any sequence of them; the server always receives a list. Each parcel is priced, verified, created, booked with the courier, and covered by one receipt. It is **not idempotent** and the SDK never retries it (the SDK retries nothing). A batch stops at the first failing parcel, and parcels created before that failure remain. On `PostwayBusinessError`, look them up by `my_tracking_no` (`order_shipments.filter`) before you resubmit.
- **`order_shipments.cancel`** matches the courier `tracking_no` only, not `my_tracking_no` or refs.
- **`labels.order_shipments`**: each `tracking_nos` entry may be a `tracking_no`, `my_tracking_no` or `ref1..3`. If none match, the server returns 400.
- **`thailand.filter`**: the field filters (`sub_district`, `district`, `province`, `zip_code`) are exact matches. `shipment_provider_names` restricts results to areas served by those couriers; omit it for all (the SDK always sends at least `[]`). The response spells the zip field `zipcode`.
- **`shipment_provider_name` / `shipment_name`** take a `name` from `shipment_providers.all()`.
- **`filter` paging**: `limit` must be 1..1,000,000 and `page` ≥ 1. A page past the end wraps to page 1.

Enums `LabelSize`, `LabelOrientation`, `ReceiptSize`, `OrderShipmentStatus`, `OrderStatus`, `OrderShipmentChannel`, `StoreBillingType`, `StoreCodType`, `UserRole`, `PriceInfoDescription`, `PlanDetailRegion` and `PlanDetailType` are `StrEnum`s, and `FlashArticleCategory` is an `IntEnum`. Members compare equal to the plain wire values, which is what responses contain:

```python
from postway import OrderShipmentStatus

if parcel["order_shipment_status"] == OrderShipmentStatus.IN_TRANSIT:  # 'In-Transit'
    ...
```

## Errors

All errors extend `PostwayError`.

| Class                                                | When                                                                          | Useful attributes                                        |
| ---------------------------------------------------- | ----------------------------------------------------------------------------- | -------------------------------------------------------- |
| `PostwayApiError`                                    | Non-2xx response                                                              | `status`, `code`, `messages`, `body`, `method`, `url`    |
| `PostwayBusinessError` _(extends `PostwayApiError`)_ | 2xx response whose envelope says `isSuccess: false`                           | same                                                     |
| `PostwayRequestError`                                | Network failure, refused redirect or timeout; nothing usable came back        | `__cause__`, `method`, `url`                             |
| `PostwayConfigError`                                 | Invalid client options or call arguments, or a guarded call without a token   | —                                                        |

The server reports errors as `{"code", "isSuccess": false, "message", "data": null}` with the real HTTP status:

| HTTP | Meaning                                                                                         |
| ---- | ----------------------------------------------------------------------------------------------- |
| 400  | Validation failure (`messages` may hold several entries) or business rule, e.g. order not found |
| 403  | Missing, unknown or expired token                                                               |
| 404  | Public receipt token invalid                                                                    |
| 500  | Server error; `messages` is a generic text                                                      |

`code` in the body is **400 or 500**, not the HTTP status. Use `status` to branch. `str(error)` is the messages joined with `"; "`, or `HTTP <status>` when there are none.

Three details keep error logs safe to keep:

- `url` is the **route template** (`…/receipt/public/:token`), not the URL that was sent. Receipt tokens, tracking numbers and refs never appear in `url` or the message.
- `body` (the parsed JSON, text, or `None`) is a read-only property kept out of `args`, `str()`, `repr()` and `vars()`. Read `error.body` explicitly when you need the raw response.
- Pickling an API error (multiprocessing, task queues) drops `body`.

`order_shipments.create` and `cancel` can fail **with HTTP 201** and `isSuccess: false`, for example when verification or the courier rejects the parcel. The SDK raises `PostwayBusinessError`, so a normal return always means success.

```python
from postway import PostwayApiError, PostwayBusinessError

try:
    client.order_shipments.cancel("TH0001")
except PostwayBusinessError as error:
    log.warning("refused: %s", error.messages)
except PostwayApiError as error:
    if error.status != 403:
        raise
    log.warning("token expired")
```

## Labels and receipt files

Label and receipt endpoints return JSON, not raw bytes:

```python
class FileHttpResponse(TypedDict):
    file_name: str
    content: str  # base64
    content_type: str
    content_length: int
```

`decode_file(file)` returns `bytes`.

## Security

- **Transport**: `base_url` must be `https://`; plain `http://` is accepted only for `localhost`, `127.0.0.1` and `[::1]`. URLs with credentials, a query string, a fragment or control characters are rejected.
- **Headers**: `access_token`, `token_type` and `user_agent` are checked at construction so a pasted token with a stray line break cannot inject headers or leak into an error message.
- **Paths**: caller-supplied path parameters are percent-encoded (including `/`) and may not be empty, `.` or `..`, so a bad input cannot reach a different endpoint.
- **Redirects** are refused: the default transport never follows one, and any 3xx response raises `PostwayRequestError`. The API never redirects, and following one could re-send `Authorization` elsewhere.
- **Errors** report route templates instead of parameter values, and response bodies stay out of `str`/`repr`/`vars`/pickles (see [Errors](#errors)).
- **No retries**, so non-idempotent calls such as `create` are never sent twice.
- The SDK has **no runtime dependencies**, never logs, and never reads environment variables.
- The access token is held privately and only sent on authenticated routes. Store it in a secret manager or environment variable, never in source control.

To report a vulnerability, see [SECURITY.md](SECURITY.md).

## Units and conventions

- Weight is in **grams**. Width, length and height are in **cm**. Money is in **THB**.
- COD amount = Σ `price_per_item × amount` over `product_cods`. An empty list means a non-COD parcel.
- Timestamps arrive as ISO-8601 strings (`IsoDateString`); parse them with `datetime.fromisoformat`. The exception is `PublicReceiptResponse["created_at"]`, which is pre-formatted `yyyy/MM/dd HH:mm:ss`.
- Keys are the wire names (`snake_case`), so payloads match the Swagger docs one to one.
- Timeouts are in **seconds**.

## Development

Uses [uv](https://docs.astral.sh/uv/).

```bash
uv sync             # creates .venv with the dev tools (pytest, mypy, ruff)
make check          # ruff format --check + ruff check + mypy --strict + unit tests
make test           # unit tests only (fake transport + a loopback server, no external network)
make format         # apply ruff formatting and safe fixes
make build          # sdist + wheel into dist/
```

```
src/postway/__init__.py   public surface (__all__)
src/postway/_client.py    PostwayMerchantClient
src/postway/_http.py      HttpPipeline, Transport protocol, UrllibTransport
src/postway/_errors.py    error classes
src/postway/_environments.py, _validation.py, _files.py, _version.py
src/postway/resources/    one class per API area (auth, order_shipments, labels, ...)
src/postway/types/        TypedDict request/response types, one module per resource, plus enums
tests/unit/               mirrors src; tests/unit/support.py holds the fake transport
tests/integration/        read-only live checks, skipped without credentials
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for conventions and the release procedure.

Unit tests assert the exact method, URL, headers and body for every endpoint, plus error mapping, the 201 + `isSuccess: false` case, empty body → `None`, redirects, timeouts and network failures. The default transport is exercised against a throwaway loopback HTTP server.

Integration tests are **read-only** (ping, account info, couriers, Thailand and parcel filters, unknown tracking number → `None`, invalid token → 403). They are skipped unless both variables are set:

```bash
POSTWAY_MERCHANT_BASE_URL=https://sandbox-post.postway.co.th/merchant \
POSTWAY_MERCHANT_ACCESS_TOKEN=... \
make test-integration
```

They never create or cancel parcels.

`__version__` lives only in `src/postway/_version.py`; `pyproject.toml` reads it from there, and `tests/unit/test_package_surface.py` checks it against the installed metadata and snapshots `__all__`. Update the snapshot deliberately when the public surface changes.

## Mapping from the Node SDK

Same endpoints, wire fields, environments and error classes; names follow Python conventions.

| Node (`@th-postway/post-sdk`)                       | Python (`postway`)                                            |
| --------------------------------------------------- | ------------------------------------------------------------- |
| `new PostwayMerchantClient({ accessToken, ... })`   | `PostwayMerchantClient(access_token=..., ...)` (keyword-only) |
| `tokenType`, `baseUrl`, `environment`, `userAgent`  | `token_type`, `base_url`, `environment`, `user_agent`         |
| `timeoutMs` (milliseconds)                          | `timeout` (seconds, `float`)                                  |
| `fetch` option                                      | `transport` option (`Transport` protocol)                     |
| `{ signal, timeoutMs }` per call                    | `timeout=` per call; no cancellation signal (sync client)     |
| `auth.accountInfo()`                                | `auth.account_info()`                                         |
| `orderShipments.getByTrackingNo / getByRef`         | `order_shipments.get_by_tracking_no / get_by_ref`             |
| `orderShipments.filter / create / cancel`           | `order_shipments.filter / create / cancel`                    |
| `orderShipments.calculatePrice`                     | `order_shipments.calculate_price`                             |
| `shipmentProviders.all()`                           | `shipment_providers.all()`                                    |
| `thailand.filter()`                                 | `thailand.filter()`                                           |
| `labels.orderShipments()`                           | `labels.order_shipments()`                                    |
| `labels.receipt(no, { receiptSize })`               | `labels.receipt(no, receipt_size=...)`                        |
| `receipts.getPublic / getPublicHtml / publicUrl`    | `receipts.get_public / get_public_html / public_url`          |
| `health.ping()`                                     | `health.ping()`                                               |
| `decodeFile(file)` → `Buffer`                       | `decode_file(file)` → `bytes`                                 |
| `LabelSize.Size4x6`, `OrderShipmentStatus.InTransit`| `LabelSize.SIZE_4X6`, `OrderShipmentStatus.IN_TRANSIT`        |
| interfaces (`MerchantOrderShipmentData`, ...)       | `TypedDict`s with the same names and keys                     |
| `PostwayError` and subclasses                       | same names; `cause` → `__cause__`                             |
| `MERCHANT_BASE_URLS`, `SDK_VERSION`                 | `MERCHANT_BASE_URLS` (read-only mapping), `__version__`       |
| `null`                                              | `None`                                                        |

Deliberate differences:

- **Sync only.** Calls block; there is no `AbortSignal` equivalent. Run calls in a thread pool if you need concurrency.
- **Timeout granularity.** The default `UrllibTransport` applies `timeout` to each socket operation (connect, each read), not as a total deadline. Its timeout message reads `… timed out after <n> s`.
- **Redirects** surface as `PostwayRequestError("… failed: redirect refused (HTTP 3xx)")`, the counterpart of Node's `redirect: 'error'`.
- **Versioning.** The Python package starts at `1.0.0` and versions independently; the Node package's major (22) tracks its Node runtime.
