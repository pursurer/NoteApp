# Class 7 - Login fix (NotesApp flaw #4 closed)

**Student:** HAOJIE SONG (2023905496). Individual work.  
**Date:** 31 October 2026.

## Audit

```
LOGIN FIX — NotesApp flaw #4 (auth) closed
  Fix 1:  verify_jwt rejects alg:none and pins algorithm to HS256
  Fix 2:  JWT_SECRET is long + random, read from the environment (no s3cr3t, no default)
  Proof:  alg:none token        -> {"error":"unauthorized"}   (expect: unauthorized)
          s3cr3t-signed token   -> {"error":"unauthorized"}   (expect: unauthorized)
          real alice login      -> works: dashboard shows her 2 grades;
                                   her new token reads /api/notes/1   (expect: works)
```

## Required change

The Class 7 deck, actual PDF page 9 (printed 04/11), and the course page *Class 7 › Fix the
login* ask for three rules held by the server: reject `none`, accept only HS256, and use a long
random secret from the environment. The test is the two forged tokens from
[Class 6](class6-forged-token.md) plus one real login.

## The change

**Fix 1 — `verify_jwt` in `web/app.py`.** The server decides the algorithm; the header gets no vote:

```python
if header.get("alg") != "HS256":
    return None
signing_input = f"{h_b64}.{p_b64}".encode()
expected = _b64url(hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest())
if not hmac.compare_digest(expected, sig_b64):
    return None
return payload
```

`none`, `None`, `hs256`, `HS512` and a missing `alg` are all rejected, because none of them is
exactly `HS256`.

**Fix 2 — the secret.** `web/app.py` now reads `JWT_SECRET = os.environ["JWT_SECRET"]` with no
default, and stops at startup if the value is shorter than 32 characters.
The value is not written in `docker-compose.yml`. The repository is public, and a secret in Git
is in every clone. Instead, the launcher (`web/key_config.py`) uses the same mechanism as the
Class 3 and Class 4 keys: on the first start it creates 32 random bytes from Python `secrets` in
the key volume (`JWT_SECRET_FILE`, mode 0600), and passes them to the app as `JWT_SECRET`
(64 hex characters, 256 bits). The secret stays the same across restarts.

In real life the secret comes from a secrets store (for example Docker or Kubernetes secrets, or
Vault), never from a committed file. If `JWT_SECRET` is already set in the environment, the
launcher keeps that value and does not create a file.

## Verification

| Request (`/api/notes/3` unless noted) | Before | After Fix 1 | After Fix 2 |
|---|---|---|---|
| Forged `alg:none` teacher token | bob's note | `unauthorized` | `unauthorized` |
| Forged HS256 token signed with `s3cr3t` | bob's note | bob's note | `unauthorized` |
| alice's token issued before the fix (`/api/notes/1`) | — | — | `unauthorized` |
| alice logs in again, new token (`/api/notes/1`) | — | — | her note (grade 16.2) |

The middle column is what the lab predicts: Fix 1 alone does not stop a token with a real seal.
After the new secret, every token issued with `s3cr3t` is invalid, including alice's old one. A
user logs in again and receives a token signed with the new secret.

The app refuses to start without `JWT_SECRET` (`KeyError: 'JWT_SECRET'`), and with
`JWT_SECRET=s3cr3t` (`RuntimeError: JWT_SECRET must be a long random value`).
In the web container, 50 tests pass, including the 4 in `web/test_jwt.py`: the header cannot
choose the algorithm, the old secret and a changed payload are rejected, and a forged token
gets `401` from `/api/notes/3`.

## Not changed in this lab

- `SECRET_KEY` for the Flask session cookie is still the fixed value `dev-session-key`. The API
  also accepts that session, so a guessable session key is the same weakness on the other ticket.
  Not tested here.
- The session cookie is `HttpOnly`, but has no `Secure` and no `SameSite` (deck actual PDF page 14).
  The app runs on plain HTTP after the Class 5 cleanup.
- The image still has the world-writable `/app/config.env` with the old value `s3cr3t`
  (flaw #6). The app does not read it, so the value is useless now, but the file is still there.
- Any logged-in user can read any note id (flaw #7, access control, next classes).
