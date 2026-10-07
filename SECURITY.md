# Security policy

## Supported versions

Only the latest major release of `th-postway-post-sdk` receives security fixes.

## Reporting a vulnerability

Please do **not** open a public issue for security problems.

Use GitHub's private vulnerability reporting on this repository: open the **Security** tab and choose **Report a vulnerability**. Include the SDK version, the Python version, a description of the issue, and steps to reproduce it.

You will receive an acknowledgement within three business days. Confirmed issues are fixed in the next patch release and credited in the changelog unless you prefer otherwise.

## What the SDK guarantees

- `base_url` must be `https://`; plain `http://` is accepted only for loopback hosts.
- Header values (`access_token`, `token_type`, `user_agent`) are validated at construction so they cannot inject headers.
- Caller-supplied path parameters are percent-encoded and may not be empty, `.` or `..`.
- Redirects are never followed; a 3xx response raises `PostwayRequestError`.
- Nothing is retried except one replay of an authenticated call after a 403 when `get_access_token` supplied a fresh token; the server rejected the first attempt, so non-idempotent calls are never applied twice.
- Error messages and `url` attributes never contain tokens, tracking numbers or other path parameters, and response bodies stay out of `args`, `str()`, `repr()`, `vars()` and pickles.
- The SDK has no runtime dependencies, does not log, and does not read environment variables.

If any of these do not hold, that is a vulnerability; please report it.
