# Class 9 - Injection fix (NotesApp flaws #8 and #9 closed)

**Student:** HAOJIE SONG (2023905496)

```text
INJECTION FIX — NotesApp flaws #8 (SQL injection) and #9 (command injection) closed

  SQLi proof (break):   username  admin' --   did NOT log in as admin (password = "anything")
                        because since Class 5 the password is checked in Python with Argon2,
                        not inside the SQL. The injection itself is real: username  '
                        -> "Query error: unterminated quoted string"
  SQLi fix:             login() uses a parameterised query (%s + tuple), no string gluing
  SQLi proof (closed):  same username now -> login fails ("Invalid credentials."), /admin -> 302 to login;
                        username  '  -> "Invalid credentials." (no SQL error)

  CmdI proof (break):   host  127.0.0.1; id   returned -> uid=0(root) gid=0(root) groups=0(root)
                        (and the first 2 lines of /etc/passwd)
  CmdI fix:             admin_ping() uses subprocess.run([...]) list, no shell=True
  CmdI proof (closed):  same host now -> "ping: 127.0.0.1; id; head -2 /etc/passwd: Name or service not known",
                        no id output

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

## Difference from the lab text

The lab's login query also checks `AND password = ...` inside the SQL, so `admin' --`
skips the password check. In this repo the SQL only looks up the username; the password is
verified afterwards with Argon2 (the Class 5 change). So `%s` is used for the username only,
and the Argon2 check is kept. The `admin' --` bypass did not work before the fix; the
unterminated-quote error shows that the username was still glued into the SQL.

All 49 existing regression tests pass after the fix.

Source: [Class 9 lab - Your words become commands](https://kristenpire.github.io/epita-security-labs/class9/injection/).
