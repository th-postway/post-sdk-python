# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# th-postway-post-sdk (import `postway`)

Python SDK for the Postway Merchant API, a port of `@th-postway/post-sdk` (Node) with the same endpoints, wire fields, environments, error semantics and security rules. Python >= 3.11, **zero runtime dependencies** (stdlib `urllib`), sync only, `TypedDict` models. Built with hatchling; dev tooling via uv (pytest, mypy --strict, ruff).

## Commands

- `make check`: ruff format --check + ruff check + mypy + unit tests. Run before every commit.
- `make format`: ruff format + `ruff check --fix`.
- `make test`: unit tests (fake transport plus a loopback server, no external network).
- Single test: `uv run pytest tests/unit/resources/test_labels.py::test_receipt_gets_label_receipt_with_optional_receipt_size` (or `-k <expr>`).
- `make build`: sdist + wheel into `dist/`.
- `make test-integration`: read-only live tests; skipped without `POSTWAY_MERCHANT_BASE_URL` and `POSTWAY_MERCHANT_ACCESS_TOKEN`.
- `make demo`: runs `demo/quick_start.py` (read-only, sandbox by default; `POSTWAY_DEMO_CREATE=1` creates a sandbox parcel). See `demo/README.md`.

mypy covers `src/postway`, `tests` and `demo`. Ruff's `T20` and `S` rules are on, so `print` outside `demo/` fails lint.

## Architecture

- `PostwayMerchantClient` (`_client.py`) validates options, builds one `HttpPipeline` and hands it to every resource (`client.auth`, `client.order_shipments`, ...). Resources hold no state beyond the pipeline.
- A resource method is a thin call: `self._http.request(method, path_segments, auth=..., body=..., query=..., timeout=...)`, cast to its `TypedDict`. Path is a list of segments; literal segments are plain strings, caller input is `param("name", value)`. `None`/empty query values are dropped. Routes whose response is the `{code, isSuccess, message, data}` envelope use `request_envelope`, which returns `data` and raises `PostwayBusinessError` on a 2xx with `isSuccess: false`.
- `HttpPipeline` (`_http.py`) builds the URL, headers and JSON body, resolves the access token through `_AccessTokenManager` (`_access_token.py`: provider called with `"initial"` / `"expiring"` / `"forbidden"`; expiry from `AccessToken.expires_at`, else JWT claims, else one `auth/account/info` probe), sends via the `Transport`, and maps non-2xx to `PostwayApiError`, network failures/timeouts to `PostwayRequestError`. Error URLs use the redacted route (`base_url/label/receipt/:receipt_no`), never the sent URL.
- `Transport` is a protocol (`send(TransportRequest) -> TransportResponse`); it must return error statuses rather than raise and must not follow redirects. `UrllibTransport` is the default; tests inject `FakeTransport`.

## Testing pattern

Resource tests use `setup([responses...])` from `tests/unit/support.py`, which returns `(client, transport)` wired to `BASE_URL`/`TOKEN`; then `call = only(transport)` and assert `call.method`, `call.url`, `call.body`, `call.headers["Authorization"] == AUTH`. `FakeTransport` fails on any unqueued request.

## Layout

```
src/postway/__init__.py   public surface (__all__)
src/postway/_client.py, _http.py, _access_token.py, _errors.py, _environments.py, _validation.py, _files.py, _version.py
src/postway/resources/    one class per API area, snake_case plural (order_shipments.py)
src/postway/types/        one TypedDict module per resource with the same name, plus enums.py and common.py
tests/unit/core           client, pipeline and UrllibTransport tests
tests/unit/resources      one file per resource
tests/unit/support.py     FakeTransport, setup(), json_response(), empty(), text(), api_error(), only()
tests/integration         live, read-only (marker `integration`, deselected by default)
```

## Rules

- `postway/__init__.py` `__all__` is the public surface; `tests/unit/test_package_surface.py` snapshots it. Change both together, deliberately.
- Never add a runtime dependency.
- `__version__` in `src/postway/_version.py` is the only version source (pyproject reads it; test-enforced).
- `TypedDict` keys use wire names (`snake_case`). Keep the API's model names in docstring backticks. String-enum response fields are typed `str`.
- Every endpoint gets: a resource method, types, a row in the README method catalogue, and a unit test asserting method, URL, headers and body.
- Formatting is ruff's (line length 120). Do not hand-format.

## Security rules (non-negotiable)

- `PostwayConfigError` messages never include the offending value.
- Caller-supplied path segments are wrapped in `param(name, value)` so they are validated and appear as `:name` in error URLs and messages.
- All header values pass through `src/postway/_validation.py`. `base_url` must be https (http only for loopback), with no credentials, query or fragment.
- Redirects stay refused (redirect handler + 3xx check in the pipeline). No retries, except the single replay of an authenticated call after a 403 when `get_access_token` refreshed the token (`_access_token.py`).
- No `print`, no `logging`, no `os.environ` reads in `src/`.
- No tokens, tracking numbers, refs or response bodies in error messages. `PostwayApiError.body` stays out of `args`/`str`/`repr`/`vars`/pickles.
- No internal infrastructure names (hosts, ports, service/framework names, private package names) anywhere in code, comments, tests or docs. Public hosts are only the two in `src/postway/_environments.py`.

## Release

git-flow with default settings; versions are SemVer `MAJOR.MINOR.PATCH` with no `v` prefix. `git flow release start 1.x.y` from `develop`, bump `__version__`, update `CHANGELOG.md`, commit, push the release branch (CI checks branch == version), `git flow release finish 1.x.y` (merges to `main`, tags `1.x.y`, merges back to `develop`), then `git push --atomic origin main develop 1.x.y`. The Publish workflow runs only for `MAJOR.MINOR.PATCH` tags, checks the tag is on `main` and equals the version, runs `make check`, and publishes to PyPI via trusted publishing. Full steps in CONTRIBUTING.md.
