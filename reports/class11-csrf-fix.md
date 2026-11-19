# Class 11 - CSRF fix (NotesApp flaw #11 closed)

**Student:** HAOJIE SONG (2023905496)

```text
CSRF FIX — NotesApp flaw #11 closed

  Break:  logged in as prof.turing, opened localhost:9000/prize.html
          note 10 became -> 19.5, "Changed by Eve's page."

  Fix:    per-session token (secrets.token_urlsafe), checked on every POST,
          hidden csrf_token field in teacher.html (1 form) + admin.html (3 forms)

  Closed: same page now -> 400 Bad Request ("CSRF token missing or wrong"), grade unchanged

  Real use still works: teacher saves a grade [x]  admin adds a user [x]  admin ping [x]
```

The fix in [`web/app.py`](../web/app.py) follows the teacher's three pieces: `SESSION_COOKIE_SAMESITE = "Lax"`
(defence in depth), `csrf_token()` (one `secrets.token_urlsafe(32)` per session, exposed to Jinja), and a
`@app.before_request` check that refuses every POST except `login` unless
`not expected or not hmac.compare_digest(sent, expected)` is false. The check fails closed: a session with no token
refuses every POST. Every real form starts with
`<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.

## Two changes beyond the lab text

This clone has a fifth POST form that the lab does not mention, so I made two changes the lab does not list.

1. `verify_export.html` (`POST /verify-export`, the Class 4 CSV check) also carries the hidden field. With a global
   check it would otherwise return 400 for every real teacher upload.
2. `/verify-export` bounds the request body before Flask parses it. Reading `request.form` in `check_csrf` parses the
   body first, which would defeat that bound, so `check_csrf` applies the same limit (`MAX_EXPORT_UPLOAD + 64 KiB`,
   `413`) before it reads the form. An 11 MB upload still returns 413.

The existing tests posted without a token, so `test_comment_encryption.py` and `test_csv_integrity.py` now put a token in
the session and send it; their assertions are unchanged. New [`web/test_csrf.py`](../web/test_csrf.py) adds 8 tests
(no token, wrong token, fail closed, correct token, login exempt, a token in every POST form, SameSite, body bound).

## How the proofs were taken

Everything ran on my own NotesApp clone, in an isolated docker project with a fresh database (seed data only).

- **Break (Part 1, curl).** Teacher cookie plus `Origin: http://evil.example`: `forged request: HTTP 302`.
  Eve's dashboard then showed `20.0` and `Perfect work.`
- **Break (Part 2, real browser).** `prize.html` was served on `localhost:9000`. I logged in as `prof.turing` on
  `localhost:8080` and opened Eve's link in the same tab, clicking nothing. The page redirected to the teacher page
  and the All grades row read `10 eve Mathematics 19.5 Changed by Eve's page.`
- **Closed (Part 4, curl).** After logging in again: no token `HTTP 400` (also with the evil `Origin`); a wrong token
  `400`; a token copied from another teacher session `400`; a session with no token yet `400`.
  The real form (token read from `/teacher`) returned `HTTP 302` and Eve's note 10 was back to `9.1`.
- **Closed (browser).** The same `prize.html` page now lands on `400 Bad Request - CSRF token missing or wrong`, and
  note 10 does not change.
- **Real use (browser).** The teacher form saved a grade (9.1 to 9.3). As admin, Add user and Ping `127.0.0.1` worked
  (`1 packets transmitted, 1 received`) and so did delete. The admin page had 37 forms and 37 token fields.
  `/verify-export` accepts a real export with a token (`200`, `valid.`) and refuses the same upload without one (`400`).
- **Tests.** 57 tests pass (the earlier 49 plus 8 new). Removing `not expected or` from the check makes
  `test_session_without_a_token_fails_closed` fail, so the new test does cover that warning.

Not changed, on purpose: `/login` stays exempt, as in the lab, so the session token is not renewed at login.
Old curl commands from earlier classes now need the token fetched first.

Source: [Class 11 lab - Requests you never meant to send](https://kristenpire.github.io/epita-security-labs/class11/csrf/).
