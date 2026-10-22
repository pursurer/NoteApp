# NotesApp

A small grades application used throughout the Computer Security course. Teachers
record grades and comments for their classes, students read their own grades, and an
admin manages users and classes.

Class 4 adds HMAC-SHA256 to CSV exports and a teacher-only verification page.
See [the Class 4 instructions](session04/README.zh-CN.md) for use and tests.

Class 5 HTTP capture evidence and Finding 1 are in [session05](session05/README.zh-CN.md).
HTTPS is now running locally with nginx and a self-signed certificate; see
[Parts 2-4 and the transit audit](session05/https/README.zh-CN.md) for the tested
configuration, actual TLS capture, certificate comparison, and native GUI evidence.

Class 5 password storage now upgrades legacy plaintext accounts to Argon2id on
successful login. Alice has migrated and logged in again; see the
[password audit summary](session05/passwords/AUDIT-SUMMARY.md) for both findings
and the measured guessing-speed comparison.

## P1, C3 and C4 delivery

- P1 group: **ZIQIAN YU (2023902046)**; **HAOJIE SONG (2023905496)**.
- [P1 risk report](session03/project1/REPORT.md): diagram with TB1-TB7 and 21 flows, six STRIDE categories, 18 scored risks, and the top three fixes.
- [Three-minute speaking script](session03/project1/PRESENTATION-3min.md).
- C3 AES-256-GCM and C4 HMAC-SHA256 are integrated into **web/app.py**.
- [Requirement-by-requirement acceptance](P1-C3-C4-REQUIREMENTS.md).

The P1 report analyses the original baseline. Its source references resolve in
`session03/project1/baseline/`, pinned to commit `8d5916436b7516547898b17fc856a54807b3638f`.

## Run it

For a fresh local copy, Docker with Compose is required:

```bash
docker compose up -d --build --wait
```

Open <http://127.0.0.1:8080>. Startup retains or creates separate persistent
AES and HMAC keys, migrates existing comments in one verified transaction, and
starts the app without the Flask debugger. New and updated comments are encrypted;
pages, API and signed CSV exports return the verified, readable comments.

For the existing local HTTPS environment:

```bash
docker compose -p notesapp-lab -f docker-compose.yml -f compose.lab.yml -f docker-compose.https.yml up -d --build --wait
```

Open <https://localhost>. This profile requires the existing locally generated
certificate; private certificate files are excluded from the coursework package.

The historic C3 entry point uses the same app and keeps its existing database and keys:

```bash
docker compose -p notesapp-session03 -f compose.session03.yml up -d --build --wait
```

Open <http://127.0.0.1:8083>. No second copy of the application needs to be generated.

## Keys and verification

The application reads `NOTESAPP_COMMENT_KEY` and `NOTESAPP_CSV_HMAC_KEY` from its
process environment. Both are independent 32-byte keys encoded as 64 hex characters.
The launcher loads the existing private files selected by their `_FILE` settings
into that environment. Keys are generated only for a new installation, never
printed or committed. Existing invalid keys stop startup; they are never replaced.
The DB container has no key volume. Keep each encrypted database with its key volumes.

Run the 45 current checks in the running default web container:

```bash
docker compose exec -T -e NOTESAPP_RUN_APP_TESTS=1 web python runtime.py python -m unittest test_comment_encryption test_csv_integrity test_key_config test_password_storage -v
```

For the existing HTTPS instance, add the same project and Compose files used to start it.
Tests create and remove temporary notes and test accounts; production course rows remain.
CSV export requires a teacher session. The file ends in `# HMAC: <hex digest>`.
At `/verify-export`, an original file succeeds and a modified grade fails.

## Test accounts

| Role    | Username      | Password   |
|---------|---------------|------------|
| Student | `alice`       | `alicepw`  |
| Teacher | `prof.turing` | `teach123` |
| Admin   | `admin`       | `admin123` |

(There are ~30 students in total; each student's password is their username + `pw`,
e.g. `bob` / `bobpw`.)

## Stack

- Python 3.11 + Flask (server-rendered Jinja2 pages and a small JSON API)
- PostgreSQL 15
- Docker Compose (`web` and `db` services)

## Stop and retain work

```bash
docker compose stop
```

Keep `pgdata`, `commentkey`, and `csvhmackey`. Deleting keys makes existing
encrypted comments unreadable or invalidates older signed exports.
The app retains course vulnerabilities outside the C3/C4 changes; see the P1 baseline risk analysis.
