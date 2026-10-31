# Class 7 - Login fix (NotesApp flaw #4 closed)

**Student:** HAOJIE SONG (2023905496)

```
LOGIN FIX — NotesApp flaw #4 (auth) closed
  Fix 1:  verify_jwt rejects alg:none and pins algorithm to HS256
  Fix 2:  JWT_SECRET is long + random, read from the environment (no s3cr3t, no default)
  Proof:  alg:none token        -> unauthorized (expect: unauthorized)
          s3cr3t-signed token   -> unauthorized (expect: unauthorized)
          real alice login      -> works (expect: works)
```

The fixed `verify_jwt` in `web/app.py`, after the header and payload are decoded:

```python
if header.get("alg") != "HS256":
    return None
signing_input = f"{h_b64}.{p_b64}".encode()
expected = _b64url(hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest())
if not hmac.compare_digest(expected, sig_b64):
    return None
return payload
```

Near the top of `web/app.py`:

```python
JWT_SECRET = os.environ["JWT_SECRET"]   # required; no weak default
```

`docker-compose.yml`, under `web:` → `environment:`, holds `JWT_SECRET` with a long random value
from `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`. Committing it is fine for this
lab only: in real life the secret comes from a secrets store, never from a committed file.
