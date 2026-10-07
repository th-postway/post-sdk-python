from __future__ import annotations

from typing import TypedDict


class MerchantLabelOrderShipmentsRequest(TypedDict):
    """``POST label/order/shipments`` request (``MerchantLabelOrderShipmentsRequest``)."""

    #: Each entry may be a ``tracking_no``, ``my_tracking_no`` or ``ref1..3``.
    tracking_nos: list[str]
    #: A :class:`~postway.LabelSize` value.
    label_size: str
    #: A :class:`~postway.LabelOrientation` value.
    label_orientation: str
