# Class 6 - Forged token finding (NotesApp flaw #4)

**Student:** HAOJIE SONG (2023905496). Individual work.  
**Date:** 31 October 2026.

## Finding

```
FORGED-TOKEN FINDING — NotesApp flaw #4 (auth)
  What I read:   bob's grade (12.6) and comment ("Solid work, keep it up."), via /api/notes/3
  Break 1:       a JWT with "alg":"none" and no signature; role set to "teacher"
  Break 2:       cracked the HS256 secret (s3cr3t) from a wordlist; signed a real teacher token
  Why it worked: the server let the TOKEN choose how to verify, AND its secret was guessable
```

## What I did

All steps ran against my own NotesApp clone on `http://localhost:8080`, before the Class 7
fix (commit `ecd0aca`), following the course page *Class 6 › Forge a token*.

1. **Read the ticket.** After `alice` / `alicepw` logged in, the dashboard page held her JWT.
   Decoding it needed no key: header `{"alg": "HS256", "typ": "JWT"}`, payload
   `{"user_id": 6, "username": "alice", "role": "student"}`. The payload is base64, not encryption.
2. **Break 1 — no signature.** I built a token with header `{"alg": "none"}`, payload
   `{"user_id": 9999, "username": "attacker", "role": "teacher"}` and an empty signature.
   Without a token, `/api/notes/3` returned `{"error":"unauthorized"}`. With the forged token it
   returned bob's note: `"grade": 12.6`, `"comment": "Solid work, keep it up."`.
3. **Break 2 — guessed secret.** Each word of the course wordlist `jwt-secrets.txt` (15 words)
   was tried as the HMAC key for alice's real token. Word 8, `s3cr3t`, produced the same
   signature. I signed a new teacher token with `alg: HS256` and `s3cr3t`; it also returned
   bob's note. Rejecting `none` alone would not stop this token.

## Why the server believed me

The server read `alg` from the token header to decide how to check the token. The header is
written by the attacker, so `"none"` switched the check off. When the check was on, the key was a
short dictionary word, so I could make a valid seal myself.

The fix (reject `none`, pin HS256, long random secret) is in [Class 7](class7-login-fix.md).
The same request also shows flaw #7: the API never checks who owns note 3. That is an access
control flaw for a later class and is not part of this finding.
