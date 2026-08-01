from __future__ import annotations

import urllib.error
from typing import Any
from unittest.mock import patch

from purh_editorial.corrector.ai._http import post_json


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        return None


def test_post_json_returns_decoded_body_on_success() -> None:
    with patch(
        "purh_editorial.corrector.ai._http.urllib.request.urlopen",
        return_value=_FakeResponse(b'{"ok": true}'),
    ):
        result = post_json("https://example.test", {"a": 1}, headers={}, timeout=5.0)
    assert result == {"ok": True}


def test_post_json_returns_none_on_connection_error() -> None:
    with patch(
        "purh_editorial.corrector.ai._http.urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        result = post_json("https://example.test", {}, headers={}, timeout=5.0)
    assert result is None


def test_post_json_returns_none_on_malformed_json_body() -> None:
    with patch(
        "purh_editorial.corrector.ai._http.urllib.request.urlopen",
        return_value=_FakeResponse(b"pas du JSON"),
    ):
        result = post_json("https://example.test", {}, headers={}, timeout=5.0)
    assert result is None
