"""Input validation. Messages never include the offending value, so they are safe to log."""

from __future__ import annotations

import ipaddress
import math
import re
from urllib.parse import quote, urlsplit

from ._errors import PostwayConfigError

#: Largest timeout accepted, in seconds (2^31 - 1 ms, the same bound as the Node SDK).
MAX_TIMEOUT = 2_147_483.647

_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
#: Non-empty printable ASCII: what every HTTP stack accepts as a header value without complaint.
_HEADER_VALUE = re.compile(r"[\x20-\x7E]+")
#: RFC 9110 ``token``: the auth-scheme part of ``Authorization``.
_AUTH_SCHEME = re.compile(r"[A-Za-z0-9!#$%&'*+.^_`|~-]+")
_HOST_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
_HOST_NAME = re.compile(rf"{_HOST_LABEL}(?:\.{_HOST_LABEL})*\.?")
_CONTROL = re.compile(r"[\x00-\x1F\x7F]")
_DEFAULT_PORTS = {"http": 80, "https": 443}


def normalize_base_url(raw: object) -> str:
    """Validate and normalise a base URL: absolute, ``https`` (or ``http`` to a loopback host), no
    credentials, query or fragment. Returns the canonical form without trailing slashes.
    """
    not_absolute = "base_url must be an absolute URL"
    if not isinstance(raw, str) or _CONTROL.search(raw) or raw != raw.strip():
        raise PostwayConfigError(not_absolute)
    try:
        parts = urlsplit(raw)
        port = parts.port
    except ValueError:
        raise PostwayConfigError(not_absolute) from None
    scheme = parts.scheme.lower()
    host = parts.hostname
    if not scheme or not parts.netloc or not host:
        raise PostwayConfigError(not_absolute)
    if scheme != "https" and not (scheme == "http" and host in _LOOPBACK_HOSTS):
        raise PostwayConfigError("base_url must use https:// (http:// is only allowed for localhost)")
    if parts.username is not None or parts.password is not None or "@" in parts.netloc:
        raise PostwayConfigError("base_url must not contain credentials")
    if "?" in raw or "#" in raw:
        raise PostwayConfigError("base_url must not contain a query string or fragment")

    if ":" in host:
        try:
            host = f"[{ipaddress.IPv6Address(host).compressed}]"
        except ValueError:
            raise PostwayConfigError(not_absolute) from None
    else:
        try:
            host = host.encode("idna").decode("ascii")
        except UnicodeError:
            raise PostwayConfigError(not_absolute) from None
        if not _HOST_NAME.fullmatch(host):
            raise PostwayConfigError(not_absolute)
    port_part = "" if port is None or port == _DEFAULT_PORTS[scheme] else f":{port}"
    path = quote(parts.path, safe="/%:@!$&'()*+,;=")
    return f"{scheme}://{host}{port_part}{path}".rstrip("/")


def assert_timeout(value: object, name: str = "timeout") -> float:
    """A positive, finite number of seconds, at most :data:`MAX_TIMEOUT`."""
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not math.isfinite(value)
        or value <= 0
        or value > MAX_TIMEOUT
    ):
        raise PostwayConfigError(f"{name} must be a positive number of seconds (at most {MAX_TIMEOUT})")
    return float(value)


def assert_header_value(value: object, name: str) -> str:
    """A value that can go on the wire as an HTTP header without being rejected or injecting headers."""
    if not isinstance(value, str) or not _HEADER_VALUE.fullmatch(value):
        raise PostwayConfigError(
            f"{name} must be a non-empty string of printable ASCII characters (no line breaks or control characters)"
        )
    return value


def assert_auth_scheme(value: object) -> str:
    """The scheme word of ``Authorization``, e.g. ``Bearer``."""
    if not isinstance(value, str) or not _AUTH_SCHEME.fullmatch(value):
        raise PostwayConfigError('token_type must be a single HTTP authentication scheme token such as "Bearer"')
    return value


def assert_path_segment(value: object, name: str) -> str:
    """A path segment that cannot change which route the request reaches."""
    if not isinstance(value, str) or value in ("", ".", ".."):
        raise PostwayConfigError(f'{name} must be a non-empty string other than "." or ".."')
    return value
