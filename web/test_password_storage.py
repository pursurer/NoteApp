"""Integration checks against temporary accounts in the local lab database."""

import os
import unittest
import uuid


@unittest.skipUnless(os.environ.get("NOTESAPP_RUN_APP_TESTS") == "1",
                     "Run inside the local lab web container.")
class PasswordStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app
        cls.module = app

    def setUp(self):
        self.client = self.module.app.test_client()
        self.user_ids = []
        self.addCleanup(self.remove_accounts)

    def remove_accounts(self):
        conn = self.module.get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM users WHERE id = ANY(%s)", (self.user_ids,))
        finally:
            conn.close()

    def account(self, stored):
        username = "class5_check_" + uuid.uuid4().hex
        conn = self.module.get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username, password, role) "
                    "VALUES (%s, %s, 'student') RETURNING id",
                    (username, stored),
                )
                self.user_ids.append(cur.fetchone()["id"])
        finally:
            conn.close()
        return username

    def stored(self, username):
        conn = self.module.get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT password FROM users WHERE username = %s", (username,))
                return cur.fetchone()["password"]
        finally:
            conn.close()

    def login(self, username, password):
        self.client.get("/logout")
        return self.client.post("/login", data={"username": username, "password": password})

    def assert_denied(self, response):
        self.assertEqual(200, response.status_code)
        self.assertIn(b"Invalid credentials.", response.data)
        with self.client.session_transaction() as session:
            self.assertNotIn("user_id", session)

    def test_upgrade_only_on_success_and_verify_on_next_login(self):
        password = "class5 seed password"
        username = self.account(password)
        self.assert_denied(self.login(username, "wrong"))
        self.assertEqual(password, self.stored(username))
        self.assertEqual(302, self.login(username, password).status_code)
        stored = self.stored(username)
        self.assertTrue(stored.startswith("$argon2id$"))
        self.assertTrue(self.module.ph.verify(stored, password))
        self.assertEqual(200, self.client.get("/dashboard").status_code)
        self.assertEqual(302, self.login(username, password).status_code)
        self.assertEqual(stored, self.stored(username))
        self.assert_denied(self.login(username, "wrong"))
        self.assertEqual(stored, self.stored(username))

    def test_corrupt_hash_is_rejected_without_server_error(self):
        for stored in ("$argon2", "$argon2id$not-a-valid-hash"):
            with self.subTest(stored=stored):
                username = self.account(stored)
                self.assert_denied(self.login(username, stored))
                self.assertEqual(stored, self.stored(username))

    def test_hash_itself_cannot_be_used_as_password(self):
        stored = self.module.ph.hash("class5 password")
        username = self.account(stored)
        self.assert_denied(self.login(username, stored))
        self.assertEqual(stored, self.stored(username))

    def test_equal_passwords_receive_different_salts(self):
        password = "class5 ' quotation 中文"
        users = [self.account(password), self.account(password)]
        for username in users:
            self.assertEqual(302, self.login(username, password).status_code)
        hashes = [self.stored(username) for username in users]
        self.assertNotEqual(hashes[0], hashes[1])
        self.assertNotEqual(hashes[0].split("$")[4], hashes[1].split("$")[4])
        for stored in hashes:
            self.assertTrue(self.module.ph.verify(stored, password))

    def test_unknown_account_is_denied(self):
        self.assert_denied(self.login("missing_" + uuid.uuid4().hex, "wrong"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
