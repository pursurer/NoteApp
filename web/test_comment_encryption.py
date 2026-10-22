"""Test comment encryption and real PostgreSQL application paths."""

import base64
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from comment_crypto import CommentCipher, CommentIntegrityError, PREFIX


class CipherTests(unittest.TestCase):
    def setUp(self):
        self.cipher = CommentCipher(AESGCM.generate_key(bit_length=256))

    def test_round_trip_text_empty_null_and_unicode(self):
        for value in ("Good work", "", None, "Très bien. 中文.\nLine two."):
            with self.subTest(value=value):
                self.assertEqual(value, self.cipher.decrypt(1, self.cipher.encrypt(1, value)))

    def test_equal_comments_have_different_nonces_and_ciphertext(self):
        first = self.cipher.encrypt(1, "Good work")
        second = self.cipher.encrypt(1, "Good work")
        self.assertNotEqual(first, second)
        self.assertNotEqual(base64.b64decode(first[5:])[:12], base64.b64decode(second[5:])[:12])

    def test_wrong_key_is_rejected(self):
        other = CommentCipher(AESGCM.generate_key(bit_length=256))
        with self.assertRaises(CommentIntegrityError):
            other.decrypt(1, self.cipher.encrypt(1, "Good work"))

    def test_nonce_ciphertext_and_tag_tampering_are_rejected(self):
        packed = base64.b64decode(self.cipher.encrypt(1, "Good work")[5:])
        for position in (0, 12, len(packed) - 1):
            changed = bytearray(packed)
            changed[position] ^= 1
            with self.subTest(position=position), self.assertRaises(CommentIntegrityError):
                self.cipher.decrypt(1, PREFIX + base64.b64encode(changed).decode())

    def test_ciphertext_from_another_row_is_rejected(self):
        with self.assertRaises(CommentIntegrityError):
            self.cipher.decrypt(2, self.cipher.encrypt(1, "Good work"))

    def test_plaintext_null_and_invalid_envelopes_are_rejected(self):
        for value in (None, "Good work", "gcm1:", "gcm1:!!!!", "gcm2:AAAA"):
            with self.subTest(value=value), self.assertRaises(CommentIntegrityError):
                self.cipher.decrypt(1, value)

    def test_invalid_key_sizes_and_row_ids_are_rejected(self):
        for key in (b"", b"x" * 16, b"x" * 31):
            with self.assertRaises(ValueError):
                CommentCipher(key)
        for note_id in (0, -1, "1", True):
            with self.assertRaises(ValueError):
                self.cipher.encrypt(note_id, "Good work")


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app
        cls.module = app
        cls.cipher = app.COMMENT_CIPHER

    def setUp(self):
        self.client = self.module.app.test_client()
        self.created = []
        self.comment = "Session03 test: Très bien. 中文."
        self.conn = self.module.get_db()
        with self.conn.cursor() as cur:
            cur.execute("SELECT nextval(pg_get_serial_sequence('notes', 'id')) AS id")
            self.note_id = cur.fetchone()["id"]
            self.created.append(self.note_id)
            cur.execute("INSERT INTO notes (id, student_id, class_id, grade, comment) "
                        "VALUES (%s, 6, 1, 14, %s)",
                        (self.note_id, self.cipher.encrypt(self.note_id, self.comment)))

    def tearDown(self):
        self.module.COMMENT_CIPHER = self.cipher
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM notes WHERE id = ANY(%s)", (self.created,))
        self.conn.close()

    def identity(self, role="student"):
        with self.client.session_transaction() as session:
            session["user_id"] = 6 if role == "student" else 2
            session["username"] = "alice" if role == "student" else "prof.turing"
            session["role"] = role

    def stored(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT comment FROM notes WHERE id = %s", (self.note_id,))
            return cur.fetchone()["comment"]

    def test_all_seed_comments_are_encrypted_and_authenticate(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, comment FROM notes ORDER BY id")
            rows = cur.fetchall()
        self.assertGreater(len(rows), 1)
        for row in rows:
            self.assertTrue(row["comment"].startswith(PREFIX))
            self.cipher.decrypt(row["id"], row["comment"])

    def test_student_dashboard_and_api_return_plaintext(self):
        self.identity()
        response = self.client.get("/dashboard")
        self.assertEqual(200, response.status_code)
        self.assertIn(self.comment, response.get_data(as_text=True))
        response = self.client.get(f"/api/notes/{self.note_id}")
        self.assertEqual(200, response.status_code)
        self.assertEqual(self.comment, response.json["comment"])

    def test_teacher_page_and_both_csv_paths_return_plaintext(self):
        self.identity("teacher")
        response = self.client.get("/teacher")
        self.assertEqual(200, response.status_code)
        self.assertIn(self.comment, response.get_data(as_text=True))
        for path in ("/export.csv", "/export.csv?class_id=1"):
            response = self.client.get(path)
            self.assertEqual(200, response.status_code)
            payload = self.module.CSV_INTEGRITY.verify(response.data)
            rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8"))))
            self.assertTrue(any(row["comment"] == self.comment for row in rows))

    def test_teacher_update_encrypts_before_storage(self):
        self.identity("teacher")
        value = "Updated Session03 comment."
        response = self.client.post("/grades", data={"note_id": str(self.note_id),
                                    "grade": "15", "comment": value})
        self.assertEqual(302, response.status_code)
        self.assertNotIn(value, self.stored())
        self.assertEqual(value, self.cipher.decrypt(self.note_id, self.stored()))

    def test_teacher_create_encrypts_before_insert(self):
        self.identity("teacher")
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM notes")
            before = {row["id"] for row in cur.fetchall()}
        response = self.client.post("/grades", data={"student_id": "6", "class_id": "1",
                                    "grade": "15", "comment": "Created Session03 comment."})
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, comment FROM notes")
            added = [row for row in cur.fetchall() if row["id"] not in before]
        self.created.extend(row["id"] for row in added)
        self.assertEqual(302, response.status_code)
        self.assertEqual(1, len(added))
        self.assertTrue(added[0]["comment"].startswith(PREFIX))
        self.assertEqual("Created Session03 comment.",
                         self.cipher.decrypt(added[0]["id"], added[0]["comment"]))

    def test_database_constraint_rejects_plaintext_writes(self):
        import psycopg2
        with self.assertRaises(psycopg2.errors.CheckViolation):
            with self.conn.cursor() as cur:
                cur.execute("UPDATE notes SET comment = %s WHERE id = %s",
                            ("This must not enter the column.", self.note_id))
        self.assertEqual(self.comment, self.cipher.decrypt(self.note_id, self.stored()))

    def test_tampering_returns_only_a_generic_error(self):
        self.identity()
        packed = bytearray(base64.b64decode(self.stored()[5:]))
        packed[-1] ^= 1
        with self.conn.cursor() as cur:
            cur.execute("UPDATE notes SET comment = %s WHERE id = %s",
                        (PREFIX + base64.b64encode(packed).decode(), self.note_id))
        response = self.client.get(f"/api/notes/{self.note_id}")
        self.assertEqual(500, response.status_code)
        self.assertEqual({"error": "Comment verification failed."}, response.json)

    def test_wrong_runtime_key_returns_a_generic_error(self):
        self.identity()
        self.module.COMMENT_CIPHER = CommentCipher(AESGCM.generate_key(bit_length=256))
        response = self.client.get(f"/api/notes/{self.note_id}")
        self.assertEqual(500, response.status_code)
        self.assertEqual({"error": "Comment verification failed."}, response.json)

    def test_missing_key_stops_startup(self):
        env = os.environ.copy()
        env.pop("NOTESAPP_COMMENT_KEY", None)
        result = subprocess.run([sys.executable, "-c", "import app"], env=env,
                                capture_output=True, text=True, timeout=15)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("NOTESAPP_COMMENT_KEY must contain a 32-byte hex key", result.stderr)

    def test_migration_is_idempotent(self):
        result = subprocess.run([sys.executable, "migrate_comments.py"],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(0, summary["migrated"])
        self.assertTrue(summary["plaintext_digest_matches"])


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({"test": test.id(), "status": "passed"})


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordingResult).run(suite)
    summary = {"tests_run": result.testsRun, "failures": len(result.failures),
               "errors": len(result.errors), "successful": result.wasSuccessful(),
               "tests": result.records}
    Path("/tmp/homework_test_results.json").write_text(json.dumps(summary, indent=2) + "\n")
    sys.exit(0 if result.wasSuccessful() else 1)
