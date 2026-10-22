"""Create a clearly labelled coursework copy with unrelated Cookie values masked.

The original PCAP is never modified. Only its login TCP stream is retained.
Retained record lengths and TCP sequence numbers stay unchanged; IPv4 and TCP
checksums are recomputed for modified packets.
The host-loopback capture is preferred when available. Both its NULL link header
and the earlier Ethernet container capture are supported.
"""

import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HOST_SOURCE = ROOT.parent / "evidence/http-login-lo0.pcapng"
SOURCE = HOST_SOURCE if HOST_SOURCE.exists() else ROOT.parent / "evidence/http-login.pcap"
TARGET = ROOT / "evidence/http-login-sanitized.pcap"
COOKIE = re.compile(rb"(?im)^(cookie|set-cookie):[^\r\n]*")


def checksum(data):
    if len(data) % 2:
        data += b"\0"
    value = sum(struct.unpack(f"!{len(data) // 2}H", data))
    while value >> 16:
        value = (value & 0xFFFF) + (value >> 16)
    return (~value) & 0xFFFF


def mask(match):
    prefix = match.group(1) + b": [redacted]"
    if len(prefix) > len(match.group()):
        return match.group(1) + b":" + b" " * (len(match.group()) - len(match.group(1)) - 1)
    return prefix + b" " * (len(match.group()) - len(prefix))


def main():
    original = SOURCE.read_bytes()
    login = subprocess.run([
        "tshark", "-r", str(SOURCE), "-d", "tcp.port==5000,http",
        "-Y", "http.request.method == \"POST\" && http.request.uri == \"/login\"",
        "-T", "fields", "-e", "frame.number", "-e", "tcp.stream",
    ], capture_output=True, text=True, check=True).stdout.strip().splitlines()
    if len(login) != 1:
        raise ValueError("Expected exactly one captured login")
    login_frame, login_stream = login[0].split("\t")
    stream_filter = f"tcp.stream eq {int(login_stream)}"
    source_frames = subprocess.run([
        "tshark", "-r", str(SOURCE), "-Y", stream_filter, "-T", "fields", "-e", "frame.number",
    ], capture_output=True, text=True, check=True).stdout.splitlines()
    source = subprocess.run([
        "tshark", "-r", str(SOURCE), "-Y", stream_filter, "-F", "pcap", "-w", "-",
    ], capture_output=True, check=True).stdout
    link_type = struct.unpack_from("<I", source, 20)[0]
    if source[:4] != b"\xd4\xc3\xb2\xa1" or link_type not in (0, 1):
        raise ValueError("Expected little-endian NULL or Ethernet PCAP")
    output = bytearray(source[:24])
    position = 24
    headers_masked = 0
    while position < len(source):
        record = source[position:position + 16]
        if len(record) != 16:
            raise ValueError("Truncated PCAP record header")
        size = struct.unpack("<IIII", record)[2]
        position += 16
        frame = bytearray(source[position:position + size])
        position += size
        if len(frame) != size:
            raise ValueError("Truncated PCAP frame")
        ip = 4 if link_type == 0 else 14
        ipv4_link = link_type == 0 or (len(frame) >= 14 and frame[12:14] == b"\x08\x00")
        if ipv4_link and len(frame) >= ip + 40 and frame[ip] >> 4 == 4 and frame[ip + 9] == 6:
            ip_size = (frame[ip] & 15) * 4
            tcp = ip + ip_size
            ip_end = ip + struct.unpack_from("!H", frame, ip + 2)[0]
            if ip_size < 20 or ip_end > len(frame) or tcp + 20 > ip_end:
                raise ValueError("Unsupported truncated IP/TCP frame")
            payload = tcp + (frame[tcp + 12] >> 4) * 4
            ports = struct.unpack_from("!HH", frame, tcp)
            if 5000 in ports or 8080 in ports:
                rewritten, count = COOKIE.subn(mask, bytes(frame[payload:ip_end]))
                if count:
                    frame[payload:ip_end] = rewritten
                    frame[ip + 10:ip + 12] = b"\0\0"
                    frame[ip + 10:ip + 12] = struct.pack("!H", checksum(bytes(frame[ip:tcp])))
                    frame[tcp + 16:tcp + 18] = b"\0\0"
                    pseudo = bytes(frame[ip + 12:ip + 20]) + b"\0\x06" + struct.pack("!H", ip_end - tcp)
                    frame[tcp + 16:tcp + 18] = struct.pack("!H", checksum(pseudo + bytes(frame[tcp:ip_end])))
                    headers_masked += count
        output.extend(record)
        output.extend(frame)

    if headers_masked == 0 or len(output) != len(source):
        raise ValueError("Expected masked headers with unchanged record lengths")
    TARGET.write_bytes(output)
    fields = subprocess.run([
        "tshark", "-r", str(TARGET), "-d", "tcp.port==5000,http",
        "-T", "fields", "-e", "http.cookie", "-e", "http.set_cookie",
    ], capture_output=True, text=True, check=True).stdout
    for item in fields.splitlines():
        for value in item.split("\t"):
            if value.strip() and value.strip() != "[redacted]":
                raise ValueError("An unmasked Cookie field remains; do not share this copy")
    if any(value in output for value in [b"n8n-auth=", b"eyJ", b"RudderEncrypt", b"posthog="]):
        raise ValueError("An unrelated identifier remains; do not share this copy")
    form = subprocess.run([
        "tshark", "-r", str(TARGET), "-d", "tcp.port==5000,http", "-Y", "http.request.method == \"POST\"",
        "-T", "fields", "-e", "urlencoded-form.key", "-e", "urlencoded-form.value",
    ], capture_output=True, text=True, check=True).stdout.strip()
    if form != "username,password\talice,alicepw":
        raise ValueError("Demo login evidence changed unexpectedly")
    result = {
        "copy_type": "Login stream only; Cookie and Set-Cookie values masked offline",
        "source_sha256": hashlib.sha256(original).hexdigest(),
        "sanitized_sha256": hashlib.sha256(output).hexdigest(),
        "source_file": SOURCE.name,
        "source_capture_point": "macOS lo0 TCP 8080" if SOURCE == HOST_SOURCE else "web container TCP 5000",
        "source_login_frame": int(login_frame),
        "source_tcp_stream": int(login_stream),
        "sanitized_login_frame": source_frames.index(login_frame) + 1,
        "sanitized_tcp_stream": 0,
        "headers_masked": headers_masked,
        "original_modified": False,
        "record_lengths_unchanged": True,
        "modified_ipv4_tcp_checksums_recomputed": True,
        "demo_credentials_preserved": True,
        "unrelated_cookie_values_absent": True,
    }
    (ROOT / "evidence/http-sanitization.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
