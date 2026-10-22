"""Capture only the classroom web service's TCP traffic in its own container.

Run through docker exec; stdout is a PCAP, diagnostics go to stderr.
No host capture permissions, dependencies, or application changes are needed.
"""

import socket
import struct
import sys
import time


def main():
    capture = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
    capture.settimeout(0.5)
    output = sys.stdout.buffer
    output.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
    output.flush()
    deadline = time.monotonic() + 55
    login_seen_at = None
    count = 0
    print("Capturing the NotesApp container's TCP port 5000 only.", file=sys.stderr)
    while time.monotonic() < deadline:
        if login_seen_at is not None and time.monotonic() - login_seen_at > 3:
            break
        try:
            frame = capture.recv(65535)
        except socket.timeout:
            continue
        # Ethernet, IPv4, TCP. The classroom Docker network uses IPv4.
        if len(frame) < 54 or frame[12:14] != b"\x08\x00" or frame[23] != 6:
            continue
        tcp_offset = 14 + (frame[14] & 15) * 4
        if len(frame) < tcp_offset + 20:
            continue
        source, destination = struct.unpack("!HH", frame[tcp_offset:tcp_offset + 4])
        if 5000 not in (source, destination):
            continue
        now = time.time()
        output.write(struct.pack("<IIII", int(now), int(now % 1 * 1000000), len(frame), len(frame)))
        output.write(frame)
        output.flush()
        count += 1
        if b"POST /login " in frame:
            login_seen_at = time.monotonic()
    capture.close()
    print(f"Saved {count} packets; login seen: {login_seen_at is not None}.", file=sys.stderr)


if __name__ == "__main__":
    main()
