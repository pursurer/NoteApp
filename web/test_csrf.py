"""Class 11: every state-changing POST needs the session's CSRF token (flaw #11)."""

import os
import re
import unittest

CSRF = "test-csrf-token"
POST_PATHS = ("/grades", "/admin/ping", "/admin/users", "/verify-export")


@unittest.skipUnless(os.environ.get("NOTESAPP_RUN_APP_TESTS") == "1",
                     "Set NOTESAPP_RUN_APP_TESTS=1 inside the running app container.")
class CsrfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app
        cls.module = app

    def setUp(self):
        self.client = self.module.app.test_client()

    def identity(self, role, csrf=CSRF):
        with self.client.session_transaction() as session:
            session.clear()
            session.update(user_id=6, username=role, role=role)
            if csrf is not None:
                session["csrf"] = csrf

    def test_post_without_token_is_refused(self):
        self.identity("teacher")
        for path in POST_PATHS:
            self.assertEqual(400, self.client.post(path, data={"note_id": "10", "grade": "20"}).status_code, path)

    def test_post_with_wrong_token_is_refused(self):
        self.identity("teacher")
        for path in POST_PATHS:
            response = self.client.post(path, data={"csrf_token": "not-the-token"})
            self.assertEqual(400, response.status_code, path)
            self.assertIn(b"CSRF token missing or wrong", response.data)

    def test_session_without_a_token_fails_closed(self):
        # "" == "" must not count as a match when the session has no token yet.
        self.identity("teacher", csrf=None)
        for path in POST_PATHS:
            self.assertEqual(400, self.client.post(path, data={"csrf_token": ""}).status_code, path)
            self.assertEqual(400, self.client.post(path, data={}).status_code, path)

    def test_correct_token_reaches_the_route(self):
        # A student passes the CSRF check and is then turned away by the role check (302), with no write.
        self.identity("student")
        for path in ("/grades", "/admin/ping", "/admin/users"):
            self.assertEqual(302, self.client.post(path, data={"csrf_token": CSRF}).status_code, path)

    def test_login_post_is_exempt(self):
        response = self.client.post("/login", data={"username": "nobody", "password": "x"})
        self.assertEqual(200, response.status_code)
        self.assertIn(b"Invalid credentials.", response.data)

    def test_every_post_form_prints_the_session_token(self):
        for role, path in (("teacher", "/teacher"), ("teacher", "/verify-export"), ("admin", "/admin")):
            self.identity(role, csrf=None)
            html = self.client.get(path).get_data(as_text=True)
            forms = len(re.findall(r'<form method="post"', html))
            self.assertGreaterEqual(forms, 1, path)
            tokens = re.findall(r'name="csrf_token" value="([^"]+)"', html)
            self.assertEqual(forms, len(tokens), path)
            with self.client.session_transaction() as session:
                self.assertEqual({session["csrf"]}, set(tokens), path)

    def test_session_cookie_is_samesite_lax(self):
        self.assertEqual("Lax", self.module.app.config["SESSION_COOKIE_SAMESITE"])

    def test_oversize_body_is_bounded_before_the_form_is_parsed(self):
        self.identity("teacher")
        limit = self.module.MAX_EXPORT_UPLOAD + 64 * 1024
        response = self.client.post("/grades", data=b"x" * (limit + 1),
                                    content_type="application/x-www-form-urlencoded")
        self.assertEqual(413, response.status_code)


if __name__ == "__main__":
    unittest.main()
