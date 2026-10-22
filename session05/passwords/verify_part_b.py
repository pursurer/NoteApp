"""Record the first real HTTPS login migration on the preserved local lab DB.

This intentionally refuses to overwrite the original evidence or reset alice.
"""

from datetime import datetime, timezone
from http.cookiejar import CookieJar
from pathlib import Path
import hashlib
import json
import ssl
import subprocess
from urllib import parse, request

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(__file__).resolve().parent / 'evidence' / 'part-b-migration.json'
if EVIDENCE.exists():
    raise SystemExit('Original evidence exists; do not overwrite or reset the account.')


def sql(query):
    result = subprocess.run(
        ['docker', 'exec', 'notesapp-lab-db-1', 'psql', '-U', 'notesapp',
         '-d', 'notesapp', '-At', '-c', query],
        check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def alice_password():
    return sql("SELECT password FROM users WHERE username = 'alice'")


def snapshot():
    return json.loads(sql("""SELECT json_build_object(
      'users', (SELECT count(*) FROM users),
      'classes', (SELECT count(*) FROM classes),
      'enrollments', (SELECT count(*) FROM enrollments),
      'notes', (SELECT count(*) FROM notes),
      'user_metadata_md5', (SELECT md5(string_agg(row_to_json(u)::text, '' ORDER BY id))
        FROM (SELECT id, username, role, teacher_id FROM users) u),
      'other_passwords_md5', (SELECT md5(string_agg(password, '' ORDER BY id))
        FROM users WHERE username <> 'alice'),
      'notes_md5', (SELECT md5(string_agg(row_to_json(n)::text, '' ORDER BY id)) FROM notes n)
    )"""))


class RedirectLog(request.HTTPRedirectHandler):
    def __init__(self):
        self.codes = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.codes.append(code)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


redirects = RedirectLog()
context = ssl.create_default_context(cafile=str(ROOT / 'nginx/certs/notesapp.crt'))
client = request.build_opener(
    request.HTTPSHandler(context=context), request.HTTPCookieProcessor(CookieJar()), redirects,
)
base = 'https://localhost'


def login(password, expected):
    client.open(base + '/logout', timeout=15).close()
    redirects.codes.clear()
    form = parse.urlencode({'username': 'alice', 'password': password}).encode()
    with client.open(request.Request(base + '/login', data=form), timeout=15) as response:
        body = response.read()
        path = parse.urlparse(response.geturl()).path
        result = {'final_status': response.status, 'final_path': path,
                  'redirect_statuses': list(redirects.codes),
                  'invalid_credentials_shown': b'Invalid credentials.' in body}
    assert path == expected, result
    assert result['final_status'] == 200, result
    if expected == '/login':
        assert result['invalid_credentials_shown'], result
        with client.open(base + '/dashboard', timeout=15) as response:
            result['dashboard_blocked'] = parse.urlparse(response.geturl()).path == '/login'
        assert result['dashboard_blocked'], result
    else:
        assert 302 in result['redirect_statuses'], result
        assert not result['invalid_credentials_shown'], result
    return result


before = alice_password()
assert before == 'alicepw', 'alice is already migrated; do not reset it to invent a before state.'
original_data = snapshot()
wrong_before = login('class5-deliberately-wrong', '/login')
assert alice_password() == before
first_login = login('alicepw', '/dashboard')
after = alice_password()
assert after.startswith('$argon2id$v=19$m=65536,t=3,p=4$'), 'Expected teacher Argon2id defaults.'
assert after != before
second_login = login('alicepw', '/dashboard')
assert alice_password() == after, 'Already migrated login must verify, not hash the hash.'
wrong_after = login('class5-deliberately-wrong', '/login')
assert alice_password() == after
final_data = snapshot()
assert final_data == original_data, 'Unexpected changes outside alice password.'

record = {
    'verified_at': datetime.now(timezone.utc).isoformat(),
    'target': 'notesapp-lab; existing database; https://localhost/login',
    'client': 'Python urllib HTTPS form login, validating both the local certificate and hostname.',
    'tls_verification': True,
    'before': {'alice_was_seed_plaintext': before == 'alicepw', 'database': original_data},
    'wrong_password_before_migration': wrong_before,
    'first_successful_login': first_login,
    'after': {'alice_storage': '$'.join(after.split('$')[:4]) + '$...',
              'alice_hash_sha256': hashlib.sha256(after.encode()).hexdigest(),
              'plaintext_replaced': True},
    'second_successful_login': second_login,
    'second_login_hash_unchanged': True,
    'wrong_password_after_migration': wrong_after,
    'final_database': final_data,
    'only_alice_password_changed': True,
    'note': 'Other legacy accounts upgrade on their own successful login. No database reset or bulk migration.',
}
EVIDENCE.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(record, ensure_ascii=False, indent=2))
