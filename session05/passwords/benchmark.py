"""Teacher's one-run CPU benchmark, with unrounded JSON evidence.

Run inside the rebuilt web container. The timed loops match the lab scaffold.
"""

from datetime import datetime, timezone
from importlib.metadata import version
import hashlib
import json
import platform
import sys
import time

from argon2 import PasswordHasher

N = 100_000
t = time.time()
for _ in range(N):
    hashlib.md5(b"guess").hexdigest()
md5_seconds = time.time() - t
md5_rate = N / md5_seconds
print(f"MD5    : {md5_rate:,.0f} guesses/second")

ph = PasswordHasher()
t = time.time()
ph.hash("guess")
one = time.time() - t
argon2_rate = 1 / one
print(f"Argon2 : {one*1000:.0f} ms for ONE guess  ({argon2_rate:.1f} guesses/second)")

print(json.dumps({
    "measured_at": datetime.now(timezone.utc).isoformat(),
    "method": "Teacher scaffold: time.time; 100000 MD5 hashes and one default PasswordHasher.hash; single CPU-container run, not a GPU estimate.",
    "python": sys.version,
    "platform": platform.platform(),
    "argon2_cffi": version("argon2-cffi"),
    "argon2_parameters": {
        "type": ph.type.name, "memory_cost_kib": ph.memory_cost,
        "time_cost": ph.time_cost, "parallelism": ph.parallelism,
        "hash_len": ph.hash_len, "salt_len": ph.salt_len,
    },
    "md5": {"iterations": N, "seconds": md5_seconds,
            "guesses_per_second": md5_rate, "guesses_per_day": md5_rate * 86400},
    "argon2": {"iterations": 1, "seconds": one,
               "guesses_per_second": argon2_rate, "guesses_per_day": argon2_rate * 86400},
    "argon2_slowdown": md5_rate / argon2_rate,
    "daily_estimate": "Unrounded measured rate multiplied by 86400; assumes constant serial throughput for 24 hours.",
}, indent=2))
