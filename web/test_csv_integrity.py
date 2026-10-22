"""Check CSV byte integrity, persistent keys, and real application routes."""

import csv
import io
import os
from pathlib import Path
import secrets
import stat
import tempfile
import unittest

from csv_integrity import CsvIntegrity, CsvIntegrityError


class CsvIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.signer = CsvIntegrity(bytes(range(32)))
        self.payload = b"student,class,grade,comment\r\nalice,Security,14,Good work\r\n"
        self.signed = self.signer.sign(self.payload)

    def test_matches_independent_openssl_reference(self):
        # Reference computed with OpenSSL dgst -sha256 -mac HMAC, key 000102...1f.
        expected = b"3583c4caf63f7f7c444bd1f2e462f7ace6942ea728176dd35236c95a6cbce398"
        self.assertEqual(self.payload + b"# HMAC: " + expected + b"\r\n", self.signed)
        self.assertEqual(self.payload, self.signer.verify(self.signed))

    def test_grade_header_and_comment_tampering_fail(self):
        for old, new in ((b",14,", b",18,"), (b"student", b"Student"),
                         (b"Good work", b"Bad work")):
            with self.subTest(field=old), self.assertRaises(CsvIntegrityError):
                self.signer.verify(self.signed.replace(old, new, 1))

    def test_wrong_key_fails(self):
        with self.assertRaises(CsvIntegrityError):
            CsvIntegrity(secrets.token_bytes(32)).verify(self.signed)

    def test_missing_malformed_truncated_and_appended_footers_fail(self):
        invalid = [b"", self.payload, self.signed[:-1], self.signed[:-5],
                   self.signed + b"extra\r\n", self.signed + self.signed[-74:],
                   self.signed.replace(b"# HMAC: ", b"# HASH: "),
                   self.payload + b"# HMAC: " + b"z" * 64 + b"\r\n",
                   self.payload + b"# HMAC: " + b"0" * 64 + b"\r\n"]
        for index, value in enumerate(invalid):
            with self.subTest(case=index), self.assertRaises(CsvIntegrityError):
                self.signer.verify(value)

    def test_line_ending_changes_fail(self):
        with self.assertRaises(CsvIntegrityError):
            self.signer.verify(self.signed.replace(b"\r\n", b"\n"))

    def test_multiline_unicode_quotes_and_hmac_text_round_trip(self):
        stream = io.StringIO(newline="")
        row = ["alice", "Sécurité 中文", "14", 'Good, "work"\r\n# HMAC: inside a comment']
        csv.writer(stream).writerow(row)
        payload = stream.getvalue().encode("utf-8")
        verified = self.signer.verify(self.signer.sign(payload))
        self.assertEqual([row], list(csv.reader(io.StringIO(verified.decode("utf-8")))))

    def test_header_only_empty_export_round_trips(self):
        payload = b"student,class,grade,comment\r\n"
        self.assertEqual(payload, self.signer.verify(self.signer.sign(payload)))

    def test_invalid_key_and_payload_fail(self):
        for key in (b"", b"x" * 16, b"x" * 31, b"x" * 33, "x" * 32):
            with self.subTest(length=len(key)), self.assertRaises(ValueError):
                CsvIntegrity(key)
        with self.assertRaises(ValueError):
            self.signer.sign(b"data without final CRLF")

    def test_generated_key_persists_and_is_private(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "keys" / "csv-hmac.key"
            first = CsvIntegrity.from_key_file(path)
            signed = first.sign(self.payload)
            self.assertEqual(self.payload, CsvIntegrity.from_key_file(path).verify(signed))
            self.assertEqual(32, path.stat().st_size)
            self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))

    def test_invalid_existing_keys_are_never_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "csv-hmac.key"
            for value in (b"", b"invalid", b"x" * 33):
                path.write_bytes(value)
                with self.subTest(size=len(value)), self.assertRaises(ValueError):
                    CsvIntegrity.from_key_file(path)
                self.assertEqual(value, path.read_bytes())

    def test_key_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target"
            target.write_bytes(bytes(range(32)))
            path = Path(directory) / "csv-hmac.key"
            path.symlink_to(target)
            with self.assertRaises(OSError):
                CsvIntegrity.from_key_file(path)


@unittest.skipUnless(os.environ.get("NOTESAPP_RUN_APP_TESTS") == "1",
                     "Set NOTESAPP_RUN_APP_TESTS=1 inside the running app container.")
class CsvAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app
        cls.module = app

    def setUp(self):
        self.client = self.module.app.test_client()
        with self.client.session_transaction() as session:
            session.update(user_id=2, username="prof.turing", role="teacher")

    def upload(self, data):
        response = self.client.post("/verify-export", data={"file": (io.BytesIO(data), "grades.csv")})
        self.addCleanup(response.close)
        self.addCleanup(response.request.environ["wsgi.input"].close)
        return response

    def test_full_and_filtered_exports_verify_with_real_database(self):
        for path in ("/export.csv", "/export.csv?class_id=1", "/export.csv?class_id=999999"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(200, response.status_code)
                self.assertEqual("no-store", response.headers["Cache-Control"])
                payload = self.module.CSV_INTEGRITY.verify(response.data)
                rows = list(csv.reader(io.StringIO(payload.decode("utf-8"))))
                self.assertEqual(["student", "class", "grade", "comment"], rows[0])
                self.assertTrue(all(len(row) == 4 for row in rows))
                if "999999" not in path:
                    self.assertGreater(len(rows), 1)
                else:
                    self.assertEqual(1, len(rows))
                uploaded = self.upload(response.data)
                self.assertEqual(200, uploaded.status_code)
                self.assertIn(b"HMAC valid.", uploaded.data)

    def test_changed_export_is_rejected_by_server(self):
        signed = self.client.get("/export.csv").data
        response = self.upload(signed.replace(b"student", b"Student", 1))
        self.assertEqual(400, response.status_code)
        self.assertIn(b"HMAC check failed.", response.data)

    def test_grade_change_14_to_18_is_rejected_by_server(self):
        payload = b"student,class,grade,comment\r\nalice,Security,14,Good work\r\n"
        signed = self.module.CSV_INTEGRITY.sign(payload)
        response = self.upload(signed.replace(b",14,", b",18,"))
        self.assertEqual(400, response.status_code)

    def test_missing_and_unsigned_files_are_rejected(self):
        self.assertEqual(400, self.client.post("/verify-export", data={}).status_code)
        self.assertEqual(400, self.upload(b"student,class,grade,comment\r\n").status_code)

    def test_upload_size_is_bounded(self):
        limit = self.module.MAX_EXPORT_UPLOAD
        self.assertEqual(413, self.upload(b"x" * (limit + 1)).status_code)
        self.assertEqual(413, self.upload(b"x" * (limit + 100000)).status_code)

    def test_anonymous_and_student_cannot_export_or_verify(self):
        for role in (None, "student"):
            with self.client.session_transaction() as session:
                session.clear()
                if role:
                    session.update(user_id=6, username="alice", role=role)
            for path in ("/export.csv", "/verify-export"):
                self.assertEqual(302, self.client.get(path).status_code)
            self.assertEqual(302, self.upload(b"invalid").status_code)

    def test_teacher_page_exposes_export_and_verification_links(self):
        response = self.client.get("/teacher")
        self.assertEqual(200, response.status_code)
        self.assertIn(b'href="/verify-export"', response.data)
        self.assertIn(b'HMAC-SHA256', response.data)
        self.assertEqual(200, self.client.get("/verify-export").status_code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
