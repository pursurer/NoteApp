"""Record what the Chrome + lo0 HTTPS re-capture shows, without any TLS keys."""

import hashlib
import json
import subprocess
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent / "evidence"
PCAP = EVIDENCE / "https-login-lo0-browser.pcapng"
OUT = EVIDENCE / "browser-lo0-verification.json"
LOGIN_STREAM = 6


def tshark(*args):
    cmd = ["tshark", "-o", "tls.keylog_file:", "-r", str(PCAP), *args]
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


raw = PCAP.read_bytes()
fields = tshark("-T", "fields", "-e", "tcp.stream").split()
data_streams = sorted({int(s) for s in tshark(
    "-Y", "tcp.dstport == 443 && tcp.len > 0", "-T", "fields", "-e", "tcp.stream").split()})
hello = tshark("-Y", f"tcp.stream == {LOGIN_STREAM} && tls.handshake.type == 1",
               "-T", "fields", "-e", "frame.number", "-e", "tls.handshake.extensions_server_name").split()
version = tshark("-Y", f"tcp.stream == {LOGIN_STREAM} && tls.handshake.type == 2",
                 "-T", "fields", "-e", "tls.handshake.extensions.supported_version").strip()
app_frames = tshark("-Y", f"tcp.stream == {LOGIN_STREAM} && tls.record.opaque_type == 23",
                    "-T", "fields", "-e", "frame.number").split()

record = {
    "pcap": PCAP.name,
    "sha256": hashlib.sha256(raw).hexdigest(),
    "total_packets": len(fields),
    "capture_point": "macOS lo0, TCP 443 only (dumpcap, started by the user with sudo)",
    "client": "Google Chrome 155, https://localhost/login, account alice / alicepw",
    "login_time_local": "2026-10-22 13:40:17 +02:00 (nginx: POST /login 302, GET /dashboard 200)",
    "login_stream": LOGIN_STREAM,
    "login_stream_client_hello": {"frame": int(hello[0]), "server_name": hello[1]},
    "login_stream_tls_version": "TLS 1.3" if version == "0x0304" else version,
    "login_stream_application_data_frames": [int(f) for f in app_frames],
    "streams_with_client_payload": data_streams,
    "other_data_stream_note": "stream 8: curl GET /login at 13:42:16, no credentials",
    "http_packets": len(tshark("-Y", "http", "-T", "fields", "-e", "frame.number").split()),
    "plaintext_byte_checks": {s: s.encode() in raw for s in
                              ["username=", "password=", "alice", "alicepw", "POST /login"]},
    "follow_tls_stream": "Wireshark: 'TLS stream not found on the selected packet' (no session keys)",
    "session_keys_loaded": False,
    "screenshots": [
        "wireshark-https-browser-lo0-tcp-stream.png",
        "wireshark-https-browser-lo0-tls-not-found.png",
        "wireshark-https-browser-lo0-tls-follow-empty.png",
    ],
}
OUT.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(record, indent=2, ensure_ascii=False))
