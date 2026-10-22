"""Verify missing, malformed, independent, and persistent key configuration."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from comment_crypto import CommentCipher
from csv_integrity import CsvIntegrity
from key_config import environment_key, load_environment


class EnvironmentKeyTests(unittest.TestCase):
    def test_app_ciphers_accept_explicit_environment_keys(self):
        with patch.dict(os.environ, {"NOTESAPP_COMMENT_KEY": "12" * 32,
                                    "NOTESAPP_CSV_HMAC_KEY": "34" * 32}, clear=True):
            cipher = CommentCipher.from_environment()
            self.assertEqual("中文", cipher.decrypt(1, cipher.encrypt(1, "中文")))
            signer = CsvIntegrity.from_environment()
            payload = b"student,grade\r\nalice,14\r\n"
            self.assertEqual(payload, signer.verify(signer.sign(payload)))

    def test_missing_and_malformed_keys_fail_without_echoing_values(self):
        for value in (None, "", "bad secret value", "ab" * 31, "gg" * 32):
            with self.subTest(value=value), patch.dict(os.environ, {}, clear=True):
                if value is not None:
                    os.environ["NOTESAPP_COMMENT_KEY"] = value
                with self.assertRaises(ValueError) as error:
                    environment_key("NOTESAPP_COMMENT_KEY")
                if value:
                    self.assertNotIn(value, str(error.exception))

    def test_launcher_reuses_existing_files_and_exports_separate_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            env = {name + "_FILE": str(Path(folder) / name)
                   for name in ("NOTESAPP_COMMENT_KEY", "NOTESAPP_CSV_HMAC_KEY")}
            values = []
            for _ in range(2):
                with patch.dict(os.environ, env, clear=True):
                    load_environment()
                    values.append(tuple(environment_key(name) for name in
                                        ("NOTESAPP_COMMENT_KEY", "NOTESAPP_CSV_HMAC_KEY")))
            self.assertEqual(values[0], values[1])
            self.assertNotEqual(*values[0])

    def test_invalid_explicit_key_never_falls_back_to_a_file(self):
        with patch.dict(os.environ, {"NOTESAPP_COMMENT_KEY": "invalid"}, clear=True):
            with self.assertRaises(ValueError):
                load_environment()

    def test_aes_and_hmac_must_use_independent_keys(self):
        with patch.dict(os.environ, {"NOTESAPP_COMMENT_KEY": "12" * 32,
                                    "NOTESAPP_CSV_HMAC_KEY": "12" * 32}, clear=True):
            with self.assertRaises(ValueError):
                load_environment()


if __name__ == "__main__":
    unittest.main(verbosity=2)
