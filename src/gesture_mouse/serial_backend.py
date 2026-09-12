"""Host side of the serial protocol (version 1): a MouseBackend that sends frames to a device.

Frame: SOF(0xA5) VER TYPE SEQ LEN PAYLOAD CRC16, as defined in firmware/src/protocol.h.
"""

from __future__ import annotations

import struct
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum
from typing import Protocol

from gesture_mouse.errors import InputControlError

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
    return frames


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

    def _send(self, msg_type: MsgType, payload: bytes = b"") -> int:
        seq = self._seq
        self._seq = (self._seq + 1) & 0xFF
        try:
            self.stream.write(encode(msg_type, seq, payload))
        except OSError as exc:
            raise InputControlError(f"serial write failed: {exc}") from exc
        self._last_send_ms = self.clock_ms()
        return seq

    def hello(self) -> None:
        self._send(MsgType.HELLO, bytes([VERSION]))

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

    def release_all(self) -> None:
        self._send(MsgType.RELEASE_ALL)
