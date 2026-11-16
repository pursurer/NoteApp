# Class 9 - Injection fix (NotesApp flaws #8 and #9 closed)

**Student:** HAOJIE SONG (2023905496)

```text
INJECTION FIX — NotesApp flaws #8 (SQL injection) and #9 (command injection) closed

  SQLi proof (break):   username  admin' --   logged in as admin, password = (none)
  SQLi fix:             login() uses a parameterised query (%s + tuple), no string gluing
  SQLi proof (closed):  same username now -> login fails, /admin redirects to the login page

  CmdI proof (break):   host  127.0.0.1; id   returned -> uid=0(root) gid=0(root) groups=0(root)
  CmdI fix:             admin_ping() uses subprocess.run([...]) list, no shell=True
  CmdI proof (closed):  same host now -> ping fails ("Name or service not known"), no id output

  Real use still works: alice login OK [x]   plain 127.0.0.1 ping OK [x]
```

The fixed `login` query in [`web/app.py`](../web/app.py):

```python
query = "SELECT id, username, role, password FROM users WHERE username = %s"
conn = get_db()
cur = conn.cursor()
try:
    cur.execute(query, (username,))
```

The fixed `admin_ping` call:

```python
result = subprocess.run(
    ["ping", "-c", "1", host],
    capture_output=True, text=True, timeout=10,
)
```

## How the proofs were taken

The break and closed proofs for the lab's exact commands were run on a clean copy of the
teacher's starter repository, in an isolated docker project, where passwords are still plain text
and the SQL checks `AND password = ...`. There `admin' --` opened the admin page with no password
and the ping box returned `uid=0(root)`. The teacher's reference fix (`cur.execute(query, (username, password))`
and the list form of `subprocess.run`) made the same inputs fail, while alice's login and a plain ping worked.

My own repository differs in one place. Since Class 5 it stores Argon2 hashes and checks the password
in Python, so its SQL only looks up the username and the fixed query is
`WHERE username = %s` with `(username,)`. On the old code of this repository, `admin' --`
did not give an admin session (the Argon2 check still failed), but a single `'` still gave
`Query error: unterminated quoted string`, which shows the username was glued into the SQL.
The ping proof was the same on both: `uid=0(root)` before, nothing after.

All 49 existing regression tests pass after the fix, with the fixed code in this repository.

Source: [Class 9 lab - Your words become commands](https://kristenpire.github.io/epita-security-labs/class9/injection/).
