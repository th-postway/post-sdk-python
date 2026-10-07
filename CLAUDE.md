# th-postway-post-sdk (import `postway`)

Python SDK for the Postway Merchant API, a port of `@th-postway/post-sdk` (Node) with the same endpoints, wire fields, environments, error semantics and security rules. Python >= 3.11, **zero runtime dependencies** (stdlib `urllib`), sync only, `TypedDict` models. Built with hatchling; dev tooling via uv (pytest, mypy --strict, ruff).

## Commands

- `make check`: ruff format --check + ruff check + mypy + unit tests. Run before every commit.
- `make test`: unit tests (fake transport plus a loopback server, no external network).
- `make build`: sdist + wheel into `dist/`.
- `make test-integration`: read-only live tests; skipped without `POSTWAY_MERCHANT_BASE_URL` and `POSTWAY_MERCHANT_ACCESS_TOKEN`.

## Layout

```
src/postway/__init__.py   public surface (__all__)
src/postway/_client.py, _http.py, _errors.py, _environments.py, _validation.py, _files.py, _version.py
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
- Redirects stay refused (redirect handler + 3xx check in the pipeline). No retries.
- No `print`, no `logging`, no `os.environ` reads in `src/`.
- No tokens, tracking numbers, refs or response bodies in error messages. `PostwayApiError.body` stays out of `args`/`str`/`repr`/`vars`/pickles.
- No internal infrastructure names (hosts, ports, service/framework names, private package names) anywhere in code, comments, tests or docs. Public hosts are only the two in `src/postway/_environments.py`.

## Release

Bump `__version__`, update `CHANGELOG.md`, commit, tag `v1.x.y`, push the tag. The Publish workflow checks tag == version, runs `make check`, and publishes to PyPI via trusted publishing.
