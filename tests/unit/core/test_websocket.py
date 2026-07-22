from __future__ import annotations

import pytest

from tvfinance.core import ProtocolError, decode_frames, encode_frame, encode_method
from tvfinance.core.websocket import is_heartbeat


def test_frame_round_trip_and_partial_buffer() -> None:
    first = encode_frame("hello")
    second = encode_frame("世界")
    messages, remainder = decode_frames(first + second[:-1])
    assert messages == ["hello"]
    assert remainder == second[:-1]
    messages, remainder = decode_frames(remainder + second[-1])
    assert messages == ["世界"]
    assert remainder == ""


def test_encode_method_and_heartbeat() -> None:
    frame = encode_method("quote_create_session", ["qs_1"])
    assert '"m":"quote_create_session"' in frame
    assert is_heartbeat("~h~123") is True
    assert is_heartbeat("data") is False


@pytest.mark.parametrize("frame", ["bad", "~m~x~m~value"])
def test_invalid_frame(frame: str) -> None:
    with pytest.raises(ProtocolError):
        decode_frames(frame)


def test_incomplete_length_header_is_buffered() -> None:
    assert decode_frames("~m~12") == ([], "~m~12")
