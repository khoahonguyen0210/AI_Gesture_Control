from __future__ import annotations

import struct
import sys

import pytest

from gesture_mouse.config import CursorConfig
from gesture_mouse.errors import InputControlError
from gesture_mouse.gesture_recognizer import Action, ActionType, GestureState
from gesture_mouse.mouse_controller import MouseController
from gesture_mouse.serial_backend import (
    ACK_TIMEOUT_MS,
    HELLO_TIMEOUT_MS,
    Frame,
    MsgType,
    ReplyReader,
    SerialBackend,
    connect,
    crc16,
    decode,
    encode,
    open_serial_backend,
    scan,
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


def backend(replies: ReplyReader | None = None) -> tuple[SerialBackend, FakeStream, Clock]:
    stream, clock = FakeStream(), Clock()
    b = SerialBackend(stream, 100, clock, size=(1000, 800), replies=replies)
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


def test_missing_ack_releases_everything_after_the_timeout() -> None:
    b, stream, clock = backend(replies=lambda: [])
    b.mouse_down("left")
    clock.t = ACK_TIMEOUT_MS - 1
    b.tick()
    clock.t = ACK_TIMEOUT_MS
    with pytest.raises(InputControlError, match="no ACK for left button down"):
        b.tick()
    assert kinds(stream.frames()) == [MsgType.BUTTON, MsgType.HEARTBEAT, MsgType.RELEASE_ALL]


def test_a_late_ack_is_accepted_without_waiting() -> None:
    inbox: list[Frame] = []

    def replies() -> list[Frame]:
        frames = inbox[:]
        inbox.clear()
        return frames

    b, stream, clock = backend(replies=replies)
    b.click("right")
    clock.t = ACK_TIMEOUT_MS - 1
    b.tick()
    inbox.append(Frame(MsgType.ACK, 0, b"\x00"))
    clock.t = ACK_TIMEOUT_MS * 2
    b.tick()
    assert kinds(stream.frames())[:2] == [MsgType.BUTTON, MsgType.BUTTON]
    assert MsgType.RELEASE_ALL not in kinds(stream.frames())


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


def test_show_state_sends_only_changes() -> None:
    b, stream, _ = backend()
    b.show_state(GestureState.POINTING)
    b.show_state(GestureState.POINTING)
    b.show_state(GestureState.DRAGGING)
    assert [(f.type, f.payload) for f in stream.frames()] == [
        (MsgType.STATE, b"\x01"),
        (MsgType.STATE, b"\x03"),
    ]


def test_state_is_sent_again_after_release_all() -> None:
    b, stream, _ = backend()
    b.show_state(GestureState.PAUSED)
    b.release_all()
    b.show_state(GestureState.PAUSED)
    assert kinds(stream.frames()) == [MsgType.STATE, MsgType.RELEASE_ALL, MsgType.STATE]


def test_scan_keeps_the_start_of_a_frame() -> None:
    whole = encode(MsgType.HEARTBEAT, 1)
    move = encode(MsgType.MOVE, 2, b"\x01\x00\x02\x00")
    frames, rest = scan(b"\x00" + whole + move[:6])
    assert [f.seq for f in frames] == [1]
    assert rest == move[:6]
    assert [f.seq for f in scan(rest + move[6:])[0]] == [2]


class FakePort:
    """A device on the other end of a serial port. It answers every frame it receives."""

    def __init__(self, reply: str = "ack") -> None:
        self.reply = reply
        self.sent = bytearray()
        self.incoming = bytearray()
        self.closed = False

    @property
    def in_waiting(self) -> int:
        return len(self.incoming)

    def read(self, n: int) -> bytes:
        data, self.incoming = bytes(self.incoming[:n]), self.incoming[n:]
        return data

    def write(self, data: bytes) -> int:
        self.sent += data
        for f in decode(data):
            if self.reply == "silent":
                continue
            if f.type == MsgType.HELLO:
                self.incoming += encode(MsgType.HELLO_ACK, f.seq, b"\x01\x00\x01")
            elif self.reply == "nack" and f.type == MsgType.BUTTON:
                self.incoming += encode(MsgType.NACK, f.seq, bytes([f.seq, 2]))
            else:
                self.incoming += encode(MsgType.ACK, f.seq, bytes([f.seq]))
        return len(data)

    def close(self) -> None:
        self.closed = True


class StepClock(Clock):
    def sleep(self, seconds: float) -> None:
        self.t += 1


def test_connect_says_hello_and_checks_button_acks() -> None:
    port, clock = FakePort(), StepClock()
    b = connect(port, "fake", clock_ms=clock, sleep=clock.sleep)
    mc = MouseController(b, CursorConfig())
    mc.apply(Action(A.DRAG_START, 0.5, 0.5))
    mc.apply(Action(A.DRAG_END))
    clock.t += ACK_TIMEOUT_MS * 2
    b.tick()
    sent = kinds(decode(bytes(port.sent)))
    assert sent == [MsgType.HELLO, MsgType.BUTTON, MsgType.BUTTON, MsgType.HEARTBEAT]


def test_replies_are_read_before_each_write() -> None:
    port = FakePort()
    b = connect(port, "fake")
    for i in range(50):
        b.move_to(i, i)
    assert port.in_waiting == len(encode(MsgType.ACK, 0, b"\x00"))


def test_connect_without_a_device_fails_and_closes_the_port() -> None:
    port, clock = FakePort(reply="silent"), StepClock()
    with pytest.raises(InputControlError, match="no reply from a device on fake"):
        connect(port, "fake", clock_ms=clock, sleep=clock.sleep)
    assert port.closed
    assert clock.t == HELLO_TIMEOUT_MS


def test_nack_for_button_down_releases_everything() -> None:
    port, clock = FakePort(reply="nack"), StepClock()
    b = connect(port, "fake", clock_ms=clock, sleep=clock.sleep)
    b.mouse_down("left")
    with pytest.raises(InputControlError, match="device rejected left button down"):
        b.tick()
    assert kinds(decode(bytes(port.sent)))[-1] == MsgType.RELEASE_ALL
    assert clock.t < ACK_TIMEOUT_MS


def test_close_closes_the_port() -> None:
    port = FakePort()
    connect(port, "fake").close()
    assert port.closed


def test_missing_pyserial_has_an_install_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "serial", None)
    with pytest.raises(InputControlError, match=r"pip install -e \"\.\[serial\]\""):
        open_serial_backend("COM99")


def test_bad_port_is_an_input_control_error() -> None:
    pytest.importorskip("serial")
    with pytest.raises(InputControlError, match="could not open serial port"):
        open_serial_backend("nosuchscheme://x")
