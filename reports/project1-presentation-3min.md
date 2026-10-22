# Project 1 - Three-minute speaking script

**ZIQIAN YU — 2023902046**  
**HAOJIE SONG — 2023905496**

Prepared on 22 October 2026. Use the pinned baseline diagram and risk table.

## 0:00-1:00 - ZIQIAN YU

Our project analyses the original NotesApp. It stores student grades, teacher comments, and user accounts.

The diagram shows three browser roles: student, teacher, and admin. Their requests cross a trust boundary into Flask. SQL requests cross another boundary into PostgreSQL.

We also include local files, the database volume, startup configuration, and Admin Ping. Ping crosses from application input into an operating-system command.

The teacher's Compose file adds two boundaries. The web container runs as root and mounts the Docker socket and the project tree, so it can reach the host. The database port is open to the network.

Our register has twenty-one numbered flows and eighteen risks. It covers all six STRIDE categories, and every flow appears in at least one risk. Each risk has a prerequisite, evidence, likelihood, impact, and a proposed fix. We did not run attacks for this analysis.

## 1:00-2:00 - HAOJIE SONG

We score each risk by multiplying likelihood and impact. Each uses a scale from one to five. These scores are estimates, not measured probabilities.

Three risks score twenty-five. First, weak token and session checks allow forged identities. Second, the login query mixes user input with SQL. Third, anyone who reaches port 5432 can log in to the database as a superuser, with the password from the public Compose file.

Missing record ownership checks follow with twenty. The Docker socket mount scores fifteen, because an attacker first needs a command in the container.

These three rank first because each one bypasses the identity and access checks. Other controls depend on those checks working correctly.

## 2:00-3:00 - HAOJIE SONG

For the first risk, reject unsigned tokens, verify required claims, and use independent random signing keys.

For the second, use parameterized SQL, password hashing, and a database role with limited permissions.

For the third, close the database port, keep the database on an internal network, and use a secret password with a limited role.

Our current C3 implementation encrypts comments with AES-GCM. C4 signs exported CSV files with HMAC. Both are integrated into the default app.

These improvements do not replace identity or access checks. Our risk scores describe the original baseline, pinned at the teacher's commit `8d59164`. Proposed fixes must be tested against valid access and rejected access.

## Presentation cues

Show `img/project1-data-flow.svg` during the first minute. Show rows R01, R02, and R15 during the second minute.
Practice with a timer and adjust pauses.
