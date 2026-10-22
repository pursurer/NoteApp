# NotesApp

**Student:** HAOJIE SONG (2023905496)

A small grades application used throughout the Computer Security course. Teachers
record grades and comments for their classes, students read their own grades, and an
admin manages users and classes.

## Coursework

Each class changes the app in place (`web/`, `docker-compose.yml`, and the files the
lab names, such as `nginx/` and `crack/`) and adds its report to [`reports/`](reports/).
The state handed in on 22 October 2026 is tagged `submitted-2026-10-22`.

| Class | Group | Report | Change in the app |
|---|---|---|---|
| Session 2 — threat model | ZIQIAN YU (2023902046); HAOJIE SONG (2023905496) | [Data flows and STRIDE](reports/class2-threat-model.md) | — |
| Project 1 — risk analysis | ZIQIAN YU (2023902046); HAOJIE SONG (2023905496) | [Report](reports/project1-risk-analysis.md) ([PDF](reports/project1-risk-analysis.pdf)) · [3-minute script](reports/project1-presentation-3min.md) | — (analyses the original app, teacher commit `8d59164`) |
| Class 3 — symmetric encryption | ZIQIAN YU (2023902046); HAOJIE SONG (2023905496) | [Caesar, ECB vs GCM, comment encryption](reports/class3-encryption.md) | AES-256-GCM on the comment column |
| Class 4 — integrity | ZIQIAN YU (2023902046); HAOJIE SONG (2023905496) | [Signed CSV export](reports/class4-integrity.md) | HMAC-SHA256 on `/export.csv`, teacher page `/verify-export` |
| Class 5 — HTTPS and password storage | HAOJIE SONG (2023905496); ANGRAN YU (2023900899) | [Lab 1 transit audit](reports/class5-lab1-transit-audit.md) ([PDF](reports/class5-lab1-transit-audit.pdf)) · [Lab 2 password audit](reports/class5-lab2-password-audit.md) ([PDF](reports/class5-lab2-password-audit.pdf)) | nginx with TLS (`nginx/`, `docker-compose.https.yml`); Argon2 with upgrade on login; MD5 cracking in `crack/` |

After Class 5 the app runs on plain HTTP again, as the lab's cleanup step asks.
Passwords stay stored with Argon2: each seeded account upgrades at its next successful login.

## Run it

You need Docker with the Compose plugin.

```
git clone git@github.com:KristenPire/NoteApp.git notesapp
cd notesapp
docker compose up
```

The first start builds the image, launches PostgreSQL, and loads the seed data
automatically. When it is ready, open:

```
http://localhost:8080
```

For HTTPS (Class 5), first create `nginx/certs/` as the lab describes, then:

```
docker compose -f docker-compose.yml -f docker-compose.https.yml up -d --build
```

and open `https://localhost`.

## Keys and tests

On its first start the web container creates two independent 32-byte keys, one for
comment encryption (volume `commentkey`) and one for the CSV HMAC (volume `csvhmackey`),
and encrypts the existing comments before it serves requests. Keys are never printed
or committed. Keep the key volumes with the database volume: deleting a key makes the
encrypted comments unreadable or invalidates older signed exports.

Run the checks in the running web container:

```
docker compose exec -T -e NOTESAPP_RUN_APP_TESTS=1 web python runtime.py python -m unittest test_comment_encryption test_csv_integrity test_key_config test_password_storage -v
```

The tests create and remove temporary notes and test accounts; the seeded rows stay.

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

## Reset

```
docker compose down -v   # wipes the database and key volumes
docker compose up        # reloads the seed data and creates new keys
```

## Updating your fork

The course repository is sometimes updated. Your fork does **not** update by itself.
To pull the latest changes into your fork:

**Easiest (GitHub website):** open your fork, and if it says *"This branch is behind
KristenPire/NoteApp"*, click **Sync fork → Update branch**. Then, in your local clone:

```
git pull
```

**Command line (keeps your own commits):**

```
git remote add upstream https://github.com/KristenPire/NoteApp.git   # once
git fetch upstream
git merge upstream/main
git push
```

Then **rebuild**, because the app code is baked into the Docker image:

```
docker compose up --build
```

A plain `docker compose up` would keep running the old image.
