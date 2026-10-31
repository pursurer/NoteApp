"""Class 7: only HS256 tokens signed with the server's secret are accepted."""

import base64
import hashlib
import hmac
import json
import os
import unittest


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def token(header, payload, secret):
    signing_input = f"{b64(json.dumps(header).encode())}.{b64(json.dumps(payload).encode())}"
    sig = b64(hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest())
    return f"{signing_input}.{sig}"


TEACHER = {"user_id": 9999, "username": "attacker", "role": "teacher"}


@unittest.skipUnless(os.environ.get("NOTESAPP_RUN_APP_TESTS") == "1",
                     "Run inside the local lab web container.")
class JwtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app
        cls.module = app

    def test_genuine_token_is_accepted(self):
        payload = {"user_id": 6, "username": "alice", "role": "student"}
        self.assertEqual(payload, self.module.verify_jwt(self.module.make_jwt(payload)))

    def test_header_cannot_choose_the_algorithm(self):
        secret = self.module.JWT_SECRET
        unsigned = token({"alg": "none", "typ": "JWT"}, TEACHER, secret).rsplit(".", 1)[0] + "."
        self.assertIsNone(self.module.verify_jwt(unsigned))
        for header in ({"alg": "none"}, {"alg": "None"}, {"alg": "hs256"},
                       {"alg": "HS512"}, {"typ": "JWT"}):
            with self.subTest(header=header):
                self.assertIsNone(self.module.verify_jwt(token(header, TEACHER, secret)))

    def test_old_secret_and_tampered_payload_are_rejected(self):
        header = {"alg": "HS256", "typ": "JWT"}
        self.assertIsNone(self.module.verify_jwt(token(header, TEACHER, "s3cr3t")))
        genuine = self.module.make_jwt({"user_id": 6, "username": "alice", "role": "student"})
        h, _, sig = genuine.split(".")
        forged_payload = b64(json.dumps(TEACHER).encode())
        self.assertIsNone(self.module.verify_jwt(f"{h}.{forged_payload}.{sig}"))

    def test_forged_token_cannot_read_a_note(self):
        client = self.module.app.test_client()
        response = client.get("/api/notes/3", headers={
            "Authorization": "Bearer " + token({"alg": "HS256"}, TEACHER, "s3cr3t")})
        self.assertEqual(401, response.status_code)
        self.assertEqual({"error": "unauthorized"}, response.json)


if __name__ == "__main__":
    unittest.main(verbosity=2)
