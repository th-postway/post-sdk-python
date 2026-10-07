"""Caller-supplied access tokens and their automatic refresh."""

from __future__ import annotations

import base64
import binascii
import json
import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from ._errors import PostwayConfigError
from ._validation import assert_header_value

#: Why the SDK asks for a token: none yet, ≥75% of its lifetime gone, or the API answered 403.
AccessTokenRefreshReason = Literal["initial", "expiring", "forbidden"]

#: Share of a token's lifetime after which it is refreshed before use.
REFRESH_AFTER_ELAPSED = 0.75


@dataclass(frozen=True)
class AccessToken:
    """A token from ``get_access_token``, optionally with when it stops being accepted.

    :param access_token: The token sent after the token type in ``Authorization``.
    :param expires_at: Expiry as an aware ``datetime`` (naive means UTC) or an ISO 8601 string. When
        omitted the SDK reads the JWT ``exp`` claim, or asks ``auth/account/info`` once.
    """

    access_token: str = field(repr=False)
    expires_at: datetime | str | None = None


#: Supplies a fresh merchant access token. Called when there is no token, when ≥75% of the current
#: token's lifetime has elapsed, and once after a 403. Exceptions it raises propagate unchanged.
AccessTokenProvider = Callable[[AccessTokenRefreshReason], str | AccessToken]

#: Sends ``POST auth/account/info`` with a token; returns the status and parsed body.
SessionProbe = Callable[[str], tuple[int, Any]]


@dataclass(eq=False)
class _TokenState:
    value: str = field(repr=False)
    #: Epoch seconds the lifetime is measured from: JWT ``iat``, else when the SDK got the token.
    starts_at: float
    expires_at: float | None
    obtained_at: float
    #: Lifetime known, or the one probe for this token already ran.
    settled: bool
    probe_lock: threading.Lock = field(default_factory=threading.Lock)
    probe_forbidden: bool | None = None


class _AccessTokenManager:
    """Holds the current token and refreshes it through the caller's provider (thread-safe)."""

    def __init__(self, access_token: str | None, provider: AccessTokenProvider | None) -> None:
        self._provider = provider
        self._lock = threading.Lock()
        self._state = _new_state(access_token, None, _now()) if access_token is not None else None

    @property
    def configured(self) -> bool:
        """A token is set or can be obtained."""
        return self._state is not None or self._provider is not None

    @property
    def can_refresh(self) -> bool:
        """Automatic refresh (and the single 403 replay) is on."""
        return self._provider is not None

    def resolve(self, probe: SessionProbe | None) -> tuple[str, bool]:
        """Token for an authenticated call, and whether the call's one 403-triggered refresh is used up.

        With a provider: obtains the first token, learns an unknown lifetime through ``probe`` (once per
        token; a 403 there refreshes immediately) and refreshes once ≥75% of the lifetime has elapsed.
        """
        state = self._state or self._refresh(None, "initial")
        if self._provider is None:
            return state.value, False
        refreshed_after_forbidden = False
        if not state.settled and probe is not None and self._probe(state, probe):
            state = self._refresh(state, "forbidden")
            refreshed_after_forbidden = True
        if _is_expiring(state, _now()):
            state = self._refresh(state, "expiring")
        return state.value, refreshed_after_forbidden

    def refresh_after_forbidden(self, sent: str) -> str:
        """New token after ``sent`` got a 403; reuses a newer token if another call already refreshed."""
        state = self._state
        if state is not None and state.value != sent:
            return state.value
        return self._refresh(state, "forbidden").value

    def observe_session(self, sent: str, body: Any) -> None:
        """Record ``session.expired`` from an ``auth/account/info`` answer for ``sent``, if still current."""
        state = self._state
        if state is None or state.value != sent:
            return
        session = body.get("session") if isinstance(body, dict) else None
        expired = session.get("expired") if isinstance(session, dict) else None
        expires_at = _parse_iso(expired) if isinstance(expired, str) else None
        if expires_at is not None:
            state.starts_at = state.obtained_at
            state.expires_at = expires_at
            state.settled = True

    def _refresh(self, stale: _TokenState | None, reason: AccessTokenRefreshReason) -> _TokenState:
        """Concurrent callers share one provider call; a caller that saw a stale state gets the newer one."""
        with self._lock:
            current = self._state
            if current is not None and current is not stale:
                return current
            if self._provider is None:
                raise PostwayConfigError("get_access_token is required to refresh the access token")
            state = _from_provider_result(self._provider(reason), _now())
            self._state = state
            return state

    def _probe(self, state: _TokenState, probe: SessionProbe) -> bool:
        """``True`` when the probe got a 403. Any other failure just settles the token with an unknown lifetime."""
        with state.probe_lock:
            if state.probe_forbidden is None:
                try:
                    status, body = probe(state.value)
                    if 200 <= status < 300:
                        self.observe_session(state.value, body)
                    state.probe_forbidden = status == 403
                except Exception:  # the probe only informs scheduling; the real call reports its own failures
                    state.probe_forbidden = False
                finally:
                    state.settled = True
            return state.probe_forbidden


def _now() -> float:
    """Epoch seconds; the one clock token scheduling reads (tests replace it)."""
    return time.time()


def _is_expiring(state: _TokenState, now: float) -> bool:
    if state.expires_at is None:
        return False
    return now >= state.starts_at + REFRESH_AFTER_ELAPSED * (state.expires_at - state.starts_at)


def _from_provider_result(result: object, now: float) -> _TokenState:
    if isinstance(result, str):
        return _new_state(assert_header_value(result, "get_access_token result"), None, now)
    if not isinstance(result, AccessToken):
        raise PostwayConfigError("get_access_token must return a token string or an AccessToken")
    token = assert_header_value(result.access_token, "get_access_token result access_token")
    if result.expires_at is None:
        return _new_state(token, None, now)
    expires_at = (
        _timestamp(result.expires_at) if isinstance(result.expires_at, datetime) else _parse_iso(result.expires_at)
    )
    if expires_at is None:
        raise PostwayConfigError("get_access_token result expires_at must be a datetime or an ISO 8601 string")
    return _new_state(token, expires_at, now)


def _new_state(value: str, expires_at: float | None, now: float) -> _TokenState:
    if expires_at is not None:
        return _TokenState(value, now, expires_at, now, settled=True)
    jwt = _decode_jwt_times(value)
    if jwt is not None:
        expires, issued = jwt
        return _TokenState(value, issued if issued is not None else now, expires, now, settled=True)
    return _TokenState(value, now, None, now, settled=False)


def _decode_jwt_times(token: str) -> tuple[float, float | None] | None:
    """``(exp, iat)`` of a JWT in epoch seconds, read without verifying the signature (they only schedule
    a refresh). ``None`` for anything that is not a JWT with a numeric ``exp``.
    """
    parts = token.split(".")
    if len(parts) != 3 or not parts[1]:
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
    except (ValueError, binascii.Error):
        return None
    if not isinstance(payload, dict):
        return None
    exp, iat = _seconds(payload.get("exp")), _seconds(payload.get("iat"))
    if exp is None:
        return None
    return exp, (iat if iat is not None and iat < exp else None)


def _seconds(value: object) -> float | None:
    """A finite JSON number as ``float``; ``None`` otherwise (``bool`` excluded)."""
    if not isinstance(value, int | float) or isinstance(value, bool):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _parse_iso(value: str) -> float | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _timestamp(parsed)


def _timestamp(value: datetime) -> float:
    return (value if value.tzinfo is not None else value.replace(tzinfo=UTC)).timestamp()
