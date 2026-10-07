# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Runnable Quick start in `demo/` (`make demo`): read-only and sandbox by default, with an opt-in sandbox create + label (`POSTWAY_DEMO_CREATE=1`). `make check` lints and type-checks the demo. Not part of the sdist or wheel.

## [1.0.0] - 2026-10-07

Initial public release, a port of the Node SDK `@th-postway/post-sdk` 22.0.0 with the same endpoint coverage.

### Added

- `PostwayMerchantClient` with resources for auth, order shipments, shipment providers, Thailand postal areas, labels, public receipts and health.
- `TypedDict` request/response types with wire (`snake_case`) keys, and `StrEnum`/`IntEnum` wire enums (`LabelSize`, `OrderShipmentStatus`, ...).
- `decode_file()` for base64 label and receipt files.
- Typed errors: `PostwayApiError`, `PostwayBusinessError`, `PostwayRequestError`, `PostwayConfigError`.
- Pluggable `Transport` protocol with a standard-library `UrllibTransport` default; no runtime dependencies.

### Security

- `base_url` must be `https://` (plain `http://` only for loopback hosts) with no credentials, query, fragment or control characters.
- `access_token`, `token_type` and `user_agent` are validated as safe header values at construction.
- Caller-supplied path parameters are percent-encoded and may not be empty, `.` or `..`.
- Redirects are refused.
- Error `url` and messages report route templates (`receipt/public/:token`) instead of parameter values; `PostwayApiError.body` is kept out of `args`, `str`, `repr`, `vars` and pickles.
- `PostwayConfigError` messages never echo the offending input.

[Unreleased]: https://github.com/th-postway/post-sdk-python/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/th-postway/post-sdk-python/releases/tag/v1.0.0
