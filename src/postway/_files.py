from __future__ import annotations

import base64
from collections.abc import Mapping
from typing import Any


def decode_file(file: Mapping[str, Any]) -> bytes:
    """Decode the base64 ``content`` of a label/receipt file (``FileHttpResponse``) into bytes."""
    return base64.b64decode(file["content"], validate=True)
