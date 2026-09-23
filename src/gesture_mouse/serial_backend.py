"""Host side of the serial protocol (version 1): a MouseBackend that sends frames to a device.

Frame: SOF(0xA5) VER TYPE SEQ LEN PAYLOAD CRC16, as defined in firmware/src/protocol.h.
"""

from __future__ import annotations

import logging
import struct
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Protocol

from gesture_mouse.errors import InputControlError
from gesture_mouse.gesture_recognizer import GestureState

log = logging.getLogger(__name__)

SOF = 0xA5
VERSION = 0x01
MAX_PAYLOAD = 16
HEADER_SIZE = 5


class MsgType(IntEnum):
    HELLO = 0x01
    HELLO_ACK = 0x02
    MOVE = 0x10
    BUTTON = 0x11
    SCROLL = 0x12
    STATE = 0x13
    HEARTBEAT = 0x20
    RELEASE_ALL = 0x21
    ACK = 0x30
    NACK = 0x31


class NackReason(IntEnum):
    BAD_CRC = 1
    BAD_LENGTH = 2
    UNKNOWN_TYPE = 3
    BAD_VERSION = 4


BUTTONS = {"left": 0, "right": 1}

# STATE payload values, matching enum device_state in firmware/src/device.h.
STATE_CODES = {
    GestureState.IDLE: 0,
    GestureState.POINTING: 1,
    GestureState.PINCH_PENDING: 2,
    GestureState.DRAGGING: 3,
    GestureState.RIGHT_LATCHED: 4,
    GestureState.SCROLLING: 5,
    GestureState.NO_HAND: 6,
    GestureState.PAUSED: 7,
}

BAUD = 115200
HEARTBEAT_MS = 100
HELLO_TIMEOUT_MS = 2000
ACK_TIMEOUT_MS = 500


@dataclass(frozen=True)
class Frame:
    type: int
    seq: int
    payload: bytes


def crc16(data: bytes) -> int:
    """CRC-16/CCITT-FALSE: polynomial 0x1021, start 0xFFFF, no reflection, no final XOR."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def encode(msg_type: int, seq: int, payload: bytes = b"") -> bytes:
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("payload too long")
    body = bytes([VERSION, msg_type, seq & 0xFF, len(payload)]) + payload
    return bytes([SOF]) + body + struct.pack("<H", crc16(body))


def decode(data: bytes) -> list[Frame]:
    """Valid frames found in a byte string. Garbage and bad frames are skipped."""
    return scan(data)[0]


def scan(data: bytes) -> tuple[list[Frame], bytes]:
    """Like decode, but also returns the unread tail, which may hold the start of a frame."""
    frames = []
    i = 0
    while i + HEADER_SIZE + 2 <= len(data):
        if data[i] != SOF or data[i + 4] > MAX_PAYLOAD:
            i += 1
            continue
        end = i + HEADER_SIZE + data[i + 4] + 2
        if end > len(data):
            break
        body = data[i + 1 : end - 2]
        if data[i + 1] == VERSION and struct.unpack("<H", data[end - 2 : end])[0] == crc16(body):
            frames.append(Frame(data[i + 2], data[i + 3], bytes(data[i + HEADER_SIZE : end - 2])))
            i = end
        else:
            i += 1
    return frames, bytes(data[i:])


class ByteStream(Protocol):
    def write(self, data: bytes, /) -> object: ...


AckReader = Callable[[int], bool]


class SerialBackend:
    """Sends mouse actions as protocol frames. Moves are sent as relative steps.

    Call tick() regularly; it sends a heartbeat when nothing else was sent for heartbeat_ms.
    """

    def __init__(
        self,
        stream: ByteStream,
        heartbeat_ms: int,
        clock_ms: Callable[[], int],
        size: tuple[int, int] = (1920, 1080),
        ack_reader: AckReader | None = None,
    ) -> None:
        self.stream = stream
        self.heartbeat_ms = heartbeat_ms
        self.clock_ms = clock_ms
        self._size = size
        self.ack_reader = ack_reader
        self._seq = 0
        self._last_send_ms: int | None = None
        self._pos = (size[0] // 2, size[1] // 2)
        self._state: int | None = None

    def _send(self, msg_type: MsgType, payload: bytes = b"") -> int:
        seq = self._seq
        self._seq = (self._seq + 1) & 0xFF
        try:
            self.stream.write(encode(msg_type, seq, payload))
        except OSError as exc:
            raise InputControlError(f"serial write failed: {exc}") from exc
        self._last_send_ms = self.clock_ms()
        return seq

    def hello(self) -> int:
        return self._send(MsgType.HELLO, bytes([VERSION]))

    def tick(self) -> None:
        last = self._last_send_ms
        if last is None or self.clock_ms() - last >= self.heartbeat_ms:
            self._send(MsgType.HEARTBEAT)

    def size(self) -> tuple[int, int]:
        return self._size

    def move_to(self, x: int, y: int) -> None:
        dx = max(-32768, min(32767, x - self._pos[0]))
        dy = max(-32768, min(32767, y - self._pos[1]))
        if dx or dy:
            self._send(MsgType.MOVE, struct.pack("<hh", dx, dy))
            self._pos = (self._pos[0] + dx, self._pos[1] + dy)

    def _button(self, button: str, down: bool) -> None:
        seq = self._send(MsgType.BUTTON, bytes([BUTTONS[button], int(down)]))
        if down and self.ack_reader is not None and not self.ack_reader(seq):
            self.release_all()
            raise InputControlError(f"no ACK for {button} button down (seq {seq})")

    def click(self, button: str) -> None:
        self._button(button, True)
        self._button(button, False)

    def mouse_down(self, button: str) -> None:
        self._button(button, True)

    def mouse_up(self, button: str) -> None:
        self._button(button, False)

    def scroll(self, amount: int) -> None:
        self._send(MsgType.SCROLL, struct.pack("<b", max(-128, min(127, amount))))

    def set_state(self, state: int) -> None:
        self._send(MsgType.STATE, bytes([state]))

    def show_state(self, state: GestureState) -> None:
        """Sends the gesture state when it changes, so the device can show it."""
        code = STATE_CODES[state]
        if code != self._state:
            self.set_state(code)
            self._state = code

    def release_all(self) -> None:
        self._send(MsgType.RELEASE_ALL)
        self._state = None  # the device also clears its state

    def close(self) -> None:
        close = getattr(self.stream, "close", None)
        if callable(close):
            close()


class SerialLink:
    """A serial port that also reads replies. Each write reads first, so the buffer stays small."""

    def __init__(
        self,
        port: Any,
        clock_ms: Callable[[], int],
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.port = port
        self.clock_ms = clock_ms
        self.sleep = sleep
        self._rest = b""

    def _read(self) -> list[Frame]:
        waiting = self.port.in_waiting
        if not waiting:
            return []
        frames, self._rest = scan(self._rest + self.port.read(waiting))
        for f in frames:
            if f.type == MsgType.NACK and len(f.payload) == 2:
                log.warning("Device rejected frame %d (reason %d)", f.payload[0], f.payload[1])
        return frames

    def write(self, data: bytes) -> int:
        self._read()
        return int(self.port.write(data))

    def wait_reply(self, seq: int, timeout_ms: int) -> Frame | None:
        """The device's reply to frame seq (ACK, NACK, or HELLO_ACK), or None after the timeout."""
        deadline = self.clock_ms() + timeout_ms
        while True:
            for f in self._read():
                if f.seq == seq and f.type in (MsgType.ACK, MsgType.NACK, MsgType.HELLO_ACK):
                    return f
            if self.clock_ms() >= deadline:
                return None
            self.sleep(0.001)

    def close(self) -> None:
        self.port.close()


def monotonic_ms() -> int:
    return time.monotonic_ns() // 1_000_000


def connect(
    port: Any, name: str, clock_ms: Callable[[], int] = monotonic_ms, **link_args: Any
) -> SerialBackend:
    """Wraps an open port, checks that a device answers HELLO, and returns the backend."""
    link = SerialLink(port, clock_ms, **link_args)

    def ack_reader(seq: int) -> bool:
        reply = link.wait_reply(seq, ACK_TIMEOUT_MS)
        return reply is not None and reply.type == MsgType.ACK

    backend = SerialBackend(link, HEARTBEAT_MS, clock_ms, ack_reader=ack_reader)
    try:
        reply = link.wait_reply(backend.hello(), HELLO_TIMEOUT_MS)
    except OSError as exc:
        link.close()
        raise InputControlError(f"serial read failed on {name}: {exc}") from exc
    if reply is None or reply.type != MsgType.HELLO_ACK:
        link.close()
        raise InputControlError(
            f"no reply from a device on {name}. Is the Wokwi simulation running and visible?"
        )
    log.info("Device on %s answered: firmware %d.%d", name, reply.payload[1], reply.payload[2])
    return backend


def open_serial_backend(url: str) -> SerialBackend:
    """Opens a serial port or URL, for example COM5 or rfc2217://localhost:4000 (Wokwi)."""
    try:
        import serial
    except ImportError as exc:
        raise InputControlError(
            'pyserial is not installed. Install it with: python -m pip install -e ".[serial]"'
        ) from exc
    try:
        port = serial.serial_for_url(url, baudrate=BAUD, timeout=0)
    except (OSError, ValueError) as exc:
        raise InputControlError(f"could not open serial port {url}: {exc}") from exc
    return connect(port, url)
