"""Encrypt the NotesApp comment column with AES-256-GCM."""

import base64
import binascii
import json
import os
from pathlib import Path

from key_config import environment_key

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


PREFIX = "gcm1:"


class CommentIntegrityError(ValueError):
    """The stored comment is not valid for this key and row."""


class CommentCipher:
    def __init__(self, key: bytes):
        if not isinstance(key, bytes) or len(key) != 32:
            raise ValueError("Use a 32-byte AES key.")
        self._aes = AESGCM(key)

    @classmethod
    def from_environment(cls):
        return cls(environment_key("NOTESAPP_COMMENT_KEY"))

    @classmethod
    def from_file(cls, path: str):
        # Read only the new key file selected for this homework environment.
        return cls(Path(path).read_bytes())

    @staticmethod
    def _aad(note_id: int) -> bytes:
        if type(note_id) is not int or note_id <= 0:
            raise ValueError("Use a positive note ID.")
        return f"NotesApp:notes:{note_id}:comment:v1".encode("ascii")

    def encrypt(self, note_id: int, comment: str | None) -> str:
        if comment is not None and not isinstance(comment, str):
            raise TypeError("The comment must be text or None.")
        aad = self._aad(note_id)
        nonce = os.urandom(12)
        # Encrypt JSON to distinguish a null comment from an empty comment.
        plaintext = json.dumps(comment, ensure_ascii=False).encode("utf-8")
        ciphertext_and_tag = self._aes.encrypt(nonce, plaintext, aad)
        return PREFIX + base64.b64encode(nonce + ciphertext_and_tag).decode("ascii")

    def decrypt(self, note_id: int, stored: str) -> str | None:
        aad = self._aad(note_id)
        try:
            if not isinstance(stored, str) or not stored.startswith(PREFIX):
                raise ValueError("Missing envelope.")
            packed = base64.b64decode(stored[len(PREFIX):], validate=True)
            if len(packed) < 28:
                raise ValueError("Incomplete envelope.")
            plaintext = self._aes.decrypt(packed[:12], packed[12:], aad)
            value = json.loads(plaintext.decode("utf-8"))
            if value is not None and not isinstance(value, str):
                raise ValueError("Invalid comment type.")
            return value
        except (InvalidTag, ValueError, UnicodeError, binascii.Error) as exc:
            # Do not include the key, plaintext, or stored value in the error.
            raise CommentIntegrityError("Comment verification failed.") from exc

    def decrypt_rows(self, rows):
        for row in rows:
            row["comment"] = self.decrypt(row["id"], row["comment"])
        return rows
