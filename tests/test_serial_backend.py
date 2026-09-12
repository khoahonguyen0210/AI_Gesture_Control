from __future__ import annotations

import struct

import pytest

from gesture_mouse.config import CursorConfig
from gesture_mouse.errors import InputControlError
from gesture_mouse.gesture_recognizer import Action, ActionType
from gesture_mouse.mouse_controller import MouseController
from gesture_mouse.serial_backend import (
    AckReader,
    Frame,
    MsgType,
    SerialBackend,
    crc16,
    decode,
    encode,
)

A = ActionType


class FakeStream:
    def __init__(self) -> None:
        self.data = bytearray()
        self.broken = False

    def write(self, data: bytes) -> int:
        if self.broken:
            raise OSError("port closed")
        self.data += data
        return len(data)

    def frames(self) -> list[Frame]:
        return decode(bytes(self.data))


class Clock:
    def __init__(self) -> None:
        self.t = 0

    def __call__(self) -> int:
        return self.t


def backend(ack_reader: AckReader | None = None) -> tuple[SerialBackend, FakeStream, Clock]:
    stream, clock = FakeStream(), Clock()
    b = SerialBackend(stream, 100, clock, size=(1000, 800), ack_reader=ack_reader)
    return b, stream, clock


def kinds(frames: list[Frame]) -> list[int]:
    return [f.type for f in frames]


def test_crc_check_value_matches_c() -> None:
    assert crc16(b"123456789") == 0x29B1
    assert crc16(b"") == 0xFFFF


def test_encode_layout() -> None:
    frame = encode(MsgType.SCROLL, 7, b"\x05")
    assert frame[:6] == bytes([0xA5, 0x01, 0x12, 0x07, 0x01, 0x05])
    assert struct.unpack("<H", frame[6:])[0] == crc16(frame[1:6])
    with pytest.raises(ValueError):
        encode(MsgType.MOVE, 0, bytes(17))


def test_decode_skips_garbage_and_bad_frames() -> None:
    good = encode(MsgType.HEARTBEAT, 1)
    bad = bytearray(encode(MsgType.HEARTBEAT, 2))
    bad[-1] ^= 1
    stream = b"\x00\xa5\x13" + good + bytes(bad) + b"\xff" + encode(MsgType.ACK, 3, b"\x03")
    assert [(f.type, f.seq) for f in decode(stream)] == [(0x20, 1), (0x30, 3)]


def test_each_action_sends_the_right_frames() -> None:
    b, stream, _ = backend()
    mc = MouseController(b, CursorConfig())
    b.hello()
    mc.apply(Action(A.MOVE, 0.6, 0.5))
    mc.apply(Action(A.LEFT_CLICK, 0.6, 0.5))
    mc.apply(Action(A.DRAG_START, 0.6, 0.5))
    mc.apply(Action(A.DRAG_MOVE, 0.7, 0.5))
    mc.apply(Action(A.DRAG_END))
    mc.apply(Action(A.RIGHT_CLICK))
    mc.apply(Action(A.SCROLL, amount=300))
    frames = stream.frames()
    assert kinds(frames) == [
        MsgType.HELLO,
        MsgType.MOVE,
        MsgType.BUTTON,
        MsgType.BUTTON,
        MsgType.BUTTON,
        MsgType.MOVE,
        MsgType.BUTTON,
        MsgType.BUTTON,
        MsgType.BUTTON,
        MsgType.SCROLL,
    ]
    assert struct.unpack("<hh", frames[1].payload) == (99, 0)
    assert [f.payload for f in frames[2:5]] == [b"\x00\x01", b"\x00\x00", b"\x00\x01"]
    assert frames[6].payload == b"\x00\x00"
    assert frames[7].payload == b"\x01\x01"
    assert struct.unpack("<b", frames[9].payload)[0] == 127
    assert [f.seq for f in frames] == list(range(10))


def test_release_all_sends_release_frame() -> None:
    b, stream, _ = backend()
    mc = MouseController(b, CursorConfig())
    mc.apply(Action(A.DRAG_START, 0.5, 0.5))
    mc.release_all()
    assert kinds(stream.frames())[-2:] == [MsgType.BUTTON, MsgType.RELEASE_ALL]


def test_heartbeat_only_when_idle() -> None:
    b, stream, clock = backend()
    b.tick()
    clock.t = 50
    b.tick()
    clock.t = 60
    b.scroll(1)
    clock.t = 150
    b.tick()
    clock.t = 160
    b.tick()
    assert kinds(stream.frames()) == [MsgType.HEARTBEAT, MsgType.SCROLL, MsgType.HEARTBEAT]


def test_missing_ack_for_button_down_releases_everything() -> None:
    asked: list[int] = []

    def no_ack(seq: int) -> bool:
        asked.append(seq)
        return False

    b, stream, _ = backend(ack_reader=no_ack)
    with pytest.raises(InputControlError, match="no ACK"):
        b.mouse_down("left")
    assert asked == [0]
    assert kinds(stream.frames()) == [MsgType.BUTTON, MsgType.RELEASE_ALL]


def test_ack_received_continues() -> None:
    b, stream, _ = backend(ack_reader=lambda seq: True)
    b.click("right")
    assert len(stream.frames()) == 2


def test_write_error_becomes_input_control_error() -> None:
    b, stream, _ = backend()
    stream.broken = True
    with pytest.raises(InputControlError, match="serial write failed"):
        b.scroll(1)


def test_sequence_wraps_at_255() -> None:
    b, stream, clock = backend()
    for i in range(258):
        clock.t = i * 100
        b.tick()
    assert [f.seq for f in stream.frames()][254:] == [254, 255, 0, 1]


def test_large_moves_are_clamped_to_int16() -> None:
    b, stream, _ = backend()
    b.move_to(100_000, -100_000)
    dx, dy = struct.unpack("<hh", stream.frames()[0].payload)
    assert (dx, dy) == (32767, -32768)
    b.move_to(*b._pos)
    assert len(stream.frames()) == 1
