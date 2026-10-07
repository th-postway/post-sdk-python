from __future__ import annotations

from types import TracebackType
from typing import Self

from ._environments import MERCHANT_BASE_URLS, MerchantEnvironment
from ._errors import PostwayConfigError
from ._http import DEFAULT_TIMEOUT, HttpPipeline, Transport, UrllibTransport, default_user_agent
from .resources.auth import AuthResource
from .resources.health import HealthResource
from .resources.labels import LabelsResource
from .resources.order_shipments import OrderShipmentsResource
from .resources.receipts import ReceiptsResource
from .resources.shipment_providers import ShipmentProvidersResource
from .resources.thailand import ThailandResource


class PostwayMerchantClient:
    """Client for the Postway Merchant API.

    The constructor validates every option and raises :class:`PostwayConfigError` without echoing the
    offending value, so construction failures are safe to log.

    .. code-block:: python

        client = PostwayMerchantClient(access_token=os.environ["POSTWAY_ACCESS_TOKEN"])
        account = client.auth.account_info()

    :param access_token: Merchant session access token, issued to you by Postway. Required for every
        call except ``receipts.*`` and ``health.ping()``.
    :param token_type: Token type sent before the token in ``Authorization``. Default ``"Bearer"``.
    :param base_url: Full API base URL; overrides ``environment``. Must be ``https://`` (plain
        ``http://`` is accepted only for localhost) with no credentials, query string or fragment.
    :param environment: Named Postway environment, ``"production"`` (default) or ``"sandbox"``.
        Ignored when ``base_url`` is set.
    :param timeout: Per-request timeout in seconds. Default 60.
    :param transport: Object with a ``send(TransportRequest) -> TransportResponse`` method. Default
        :class:`UrllibTransport`. Inject one for proxies, tracing or tests.
    :param user_agent: ``User-Agent`` header. Default ``postway-sdk-python/<version> python/<version>``.
    """

    auth: AuthResource
    order_shipments: OrderShipmentsResource
    shipment_providers: ShipmentProvidersResource
    thailand: ThailandResource
    labels: LabelsResource
    receipts: ReceiptsResource
    health: HealthResource

    def __init__(
        self,
        *,
        access_token: str | None = None,
        token_type: str = "Bearer",  # noqa: S107 - an auth scheme, not a secret
        base_url: str | None = None,
        environment: MerchantEnvironment = "production",
        timeout: float = DEFAULT_TIMEOUT,
        transport: Transport | None = None,
        user_agent: str | None = None,
    ) -> None:
        if base_url is None:
            if environment not in MERCHANT_BASE_URLS:
                raise PostwayConfigError(
                    f"environment must be one of: {', '.join(MERCHANT_BASE_URLS)} (or pass base_url)"
                )
            base_url = MERCHANT_BASE_URLS[environment]
        if transport is None:
            transport = UrllibTransport()
        elif not callable(getattr(transport, "send", None)):
            raise PostwayConfigError("transport must provide a send(request) method")

        http = HttpPipeline(
            base_url=base_url,
            access_token=access_token or None,
            token_type=token_type,
            timeout=timeout,
            transport=transport,
            user_agent=user_agent if user_agent is not None else default_user_agent(),
        )
        self._http = http
        self.auth = AuthResource(http)
        self.order_shipments = OrderShipmentsResource(http)
        self.shipment_providers = ShipmentProvidersResource(http)
        self.thailand = ThailandResource(http)
        self.labels = LabelsResource(http)
        self.receipts = ReceiptsResource(http)
        self.health = HealthResource(http)

    @property
    def base_url(self) -> str:
        """Resolved base URL, without a trailing slash."""
        return self._http.base_url

    def close(self) -> None:
        """Release the transport, if it has anything to release."""
        close = getattr(self._http.transport, "close", None)
        if callable(close):
            close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"PostwayMerchantClient(base_url={self.base_url!r})"
