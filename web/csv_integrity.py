"""Authenticate CSV exports with a separate, persistent HMAC-SHA256 key."""

import hmac
import re

from key_config import environment_key, persistent_key


FOOTER_PREFIX = b"# HMAC: "
FOOTER_LENGTH = len(FOOTER_PREFIX) + 64 + 2


class CsvIntegrityError(ValueError):
    """The export is unsigned, malformed, or has changed."""


class CsvIntegrity:
    def __init__(self, key: bytes):
        if not isinstance(key, bytes) or len(key) != 32:
            raise ValueError("Use a separate 32-byte CSV HMAC key.")
        self._key = key

    @classmethod
    def from_environment(cls):
        return cls(environment_key("NOTESAPP_CSV_HMAC_KEY"))

    @classmethod
    def from_key_file(cls, filename):
        """Compatibility helper; the running application reads its key from env."""
        return cls(persistent_key(filename))

    def sign(self, payload: bytes) -> bytes:
        """Append the HMAC of the exact UTF-8 CSV bytes, including CRLFs."""
        if not payload.endswith(b"\r\n"):
            raise ValueError("The CSV must end with CRLF before signing.")
        tag = hmac.digest(self._key, payload, "sha256").hex().encode("ascii")
        return payload + FOOTER_PREFIX + tag + b"\r\n"

    def verify(self, signed: bytes) -> bytes:
        """Return authenticated CSV bytes. Never normalize or parse first."""
        payload, footer = signed[:-FOOTER_LENGTH], signed[-FOOTER_LENGTH:]
        tag = footer[len(FOOTER_PREFIX):-2]
        if (not payload.endswith(b"\r\n")
                or not footer.startswith(FOOTER_PREFIX)
                or not footer.endswith(b"\r\n")
                or re.fullmatch(rb"[0-9a-f]{64}", tag) is None):
            raise CsvIntegrityError("CSV verification failed.")
        expected = hmac.digest(self._key, payload, "sha256").hex().encode("ascii")
        if not hmac.compare_digest(expected, tag):
            raise CsvIntegrityError("CSV verification failed.")
        return payload
