"""Capture only encrypted TCP 443 in this lab's nginx network namespace.

Run with the existing Python image and --network container:notesapp-lab-nginx-1.
This captures the TLS ingress, not Flask's decrypted TCP 5000 traffic.
PCAP goes to stdout; capture status goes to stderr. No TLS secrets are loaded.
"""

import argparse
import socket
import struct
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=45)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 180:
        parser.error("--seconds must be between 1 and 180")

    capture = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
    capture.settimeout(0.5)
    output = sys.stdout.buffer
    output.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
    output.flush()
    deadline = time.monotonic() + args.seconds
    count = 0
    print("Capturing this lab proxy's TCP 443 ingress only.", file=sys.stderr, flush=True)
    try:
        while time.monotonic() < deadline:
            try:
                frame = capture.recv(65535)
            except socket.timeout:
                continue
            if len(frame) < 54 or frame[12:14] != b"\x08\x00" or frame[23] != 6:
                continue
            ip_size = (frame[14] & 15) * 4
            if ip_size < 20 or struct.unpack("!H", frame[20:22])[0] & 0x3FFF:
                continue
            tcp_offset = 14 + ip_size
            if len(frame) < tcp_offset + 20:
                continue
            source, destination = struct.unpack("!HH", frame[tcp_offset:tcp_offset + 4])
            if 443 not in (source, destination):
                continue
            now = time.time_ns()
            seconds, nanoseconds = divmod(now, 1_000_000_000)
            output.write(struct.pack("<IIII", seconds, nanoseconds // 1000, len(frame), len(frame)))
            output.write(frame)
            output.flush()
            count += 1
    finally:
        capture.close()
        print(f"Saved {count} TCP 443 packets.", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
