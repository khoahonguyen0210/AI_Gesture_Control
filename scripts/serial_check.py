"""Measure a serial device's reply time and lost replies.

Run: python scripts/serial_check.py rfc2217://localhost:4000
"""

from __future__ import annotations

import argparse
import statistics
import sys

from gesture_mouse.errors import InputControlError
from gesture_mouse.serial_backend import MsgType, SerialLink, encode, monotonic_ms


def measure(link: SerialLink, count: int, timeout_ms: int) -> tuple[list[int], list[int]]:
    """Sends count heartbeats. Returns reply times in ms and the sequence numbers with no ACK."""
    times, lost = [], []
    for i in range(1, count + 1):
        seq = i & 0xFF
        start = link.clock_ms()
        link.write(encode(MsgType.HEARTBEAT, seq))
        reply = link.wait_reply(seq, timeout_ms)
        if reply is not None and reply.type == MsgType.ACK:
            times.append(link.clock_ms() - start)
        else:
            lost.append(seq)
    return times, lost


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure a serial device's reply time.")
    parser.add_argument("port", help="for example rfc2217://localhost:4000 or COM5")
    parser.add_argument("--count", type=int, default=300, help="frames to send (default 300)")
    parser.add_argument("--timeout-ms", type=int, default=2000)
    args = parser.parse_args()

    try:
        import serial

        port = serial.serial_for_url(args.port, baudrate=115200, timeout=0)
    except (ImportError, OSError, ValueError) as exc:
        print(f"Could not open {args.port}: {exc}", file=sys.stderr)
        return 1
    link = SerialLink(port, monotonic_ms)
    try:
        link.write(encode(MsgType.HELLO, 0, b"\x01"))
        if link.wait_reply(0, args.timeout_ms) is None:
            raise InputControlError("no HELLO_ACK")
        times, lost = measure(link, args.count, args.timeout_ms)
    except (InputControlError, OSError) as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        return 1
    finally:
        link.close()

    print(f"{len(times)} of {args.count} frames answered")
    if times:
        median = statistics.median(times)
        p95 = statistics.quantiles(times, n=20, method="inclusive")[-1] if times[1:] else median
        print(f"reply time ms: median {median:.0f}, p95 {p95:.0f}, max {max(times)}")
    if lost:
        print(f"no ACK for sequence numbers: {lost}")
    return 0 if not lost else 1


if __name__ == "__main__":
    raise SystemExit(main())
