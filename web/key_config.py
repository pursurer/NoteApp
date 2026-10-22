"""Keep persistent lab keys separate from source and pass them to the app as env."""

import os
from pathlib import Path
import re
import secrets


def environment_key(name):
    value = os.environ.get(name, "")
    if re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
        raise ValueError(f"{name} must contain a 32-byte hex key.")
    return bytes.fromhex(value)


def persistent_key(filename):
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow, 0o600)
    except FileExistsError:
        fd = os.open(path, os.O_RDONLY | nofollow)
        with os.fdopen(fd, "rb") as stream:
            key = stream.read(33)
    else:
        key = secrets.token_bytes(32)
        with os.fdopen(fd, "wb") as stream:
            stream.write(key)
            stream.flush()
            os.fsync(stream.fileno())
    if len(key) != 32:
        raise ValueError("The existing key must contain exactly 32 bytes; it was not replaced.")
    return key


def load_environment():
    """Called by the launcher, never print values or overwrite an existing key."""
    for name, default in (
        ("NOTESAPP_COMMENT_KEY", "/run/notesapp-secrets/comments.key"),
        ("NOTESAPP_CSV_HMAC_KEY", "/run/notesapp-export/csv-hmac.key"),
    ):
        if name not in os.environ:
            os.environ[name] = persistent_key(os.environ.get(name + "_FILE", default)).hex()
        environment_key(name)
    if environment_key("NOTESAPP_COMMENT_KEY") == environment_key("NOTESAPP_CSV_HMAC_KEY"):
        raise ValueError("Use independent AES and HMAC keys.")
