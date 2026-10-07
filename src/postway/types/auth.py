from __future__ import annotations

from typing import TypedDict

from .common import IsoDateString


class MerchantAccountUser(TypedDict):
    """``MerchantAuthAccountInfoResponseUser`` — the store owner the session acts as."""

    username: str
    email: str
    first_name: str
    last_name: str
    mobile_phone: str
    #: A :class:`~postway.UserRole` value.
    role: str


class MerchantAccountStore(TypedDict):
    """``MerchantAuthAccountInfoResponseStore``."""

    code: str
    name: str
    mobile_phone: str
    #: A :class:`~postway.StoreBillingType` value.
    store_billing_type: str
    #: A :class:`~postway.StoreCodType` value.
    store_cod_type: str
    address: str
    sub_district: str
    district: str
    province: str
    zip_code: str


class MerchantAccountSession(TypedDict):
    """``MerchantAuthAccountInfoResponseSession``."""

    #: When the access token stops being accepted.
    expired: IsoDateString


class MerchantAuthAccountInfoResponse(TypedDict):
    """``POST auth/account/info`` response (``MerchantAuthAccountInfoResponse``)."""

    store: MerchantAccountStore
    user: MerchantAccountUser
    session: MerchantAccountSession
