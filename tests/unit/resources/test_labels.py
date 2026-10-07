from __future__ import annotations

import base64

from postway import (
    FileHttpResponse,
    LabelOrientation,
    LabelSize,
    MerchantLabelOrderShipmentsRequest,
    ReceiptSize,
    decode_file,
)
from tests.unit.support import AUTH, BASE_URL, json_response, only, setup

FILE: FileHttpResponse = {
    "file_name": "label.pdf",
    "content": base64.b64encode(b"%PDF-1.7").decode("ascii"),
    "content_type": "application/pdf",
    "content_length": 8,
}


def test_order_shipments_posts_label_order_shipments_decodable_with_decode_file() -> None:
    client, transport = setup([json_response(FILE, 201)])
    request: MerchantLabelOrderShipmentsRequest = {
        "tracking_nos": ["TH0001", "SHOP-2"],
        "label_size": LabelSize.SIZE_4X6,
        "label_orientation": LabelOrientation.PORTRAIT,
    }
    result = client.labels.order_shipments(request)
    call = only(transport)
    assert (call.method, call.url) == ("POST", f"{BASE_URL}/label/order/shipments")
    assert call.body == {"tracking_nos": ["TH0001", "SHOP-2"], "label_size": "4x6", "label_orientation": "Portrait"}
    assert call.headers["Content-Type"] == "application/json"
    assert call.headers["Authorization"] == AUTH
    assert decode_file(result) == b"%PDF-1.7"


def test_receipt_gets_label_receipt_with_optional_receipt_size() -> None:
    client, transport = setup([json_response(FILE), json_response(FILE)])
    client.labels.receipt("RC-001", receipt_size=ReceiptSize.R80MM)
    client.labels.receipt("RC-002")
    assert [call.url for call in transport.calls] == [
        f"{BASE_URL}/label/receipt/RC-001?receipt_size=80mm",
        f"{BASE_URL}/label/receipt/RC-002",
    ]
    assert transport.calls[0].method == "GET"
    assert transport.calls[0].headers["Authorization"] == AUTH
