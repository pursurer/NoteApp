# P1 / C3 / C4 - Requirement acceptance

Reviewed against the original teacher files after implementation on **22 October 2026**.

**Group:** ZIQIAN YU (2023902046); HAOJIE SONG (2023905496).

## P1 - Session 03, actual PDF page 31

| Teacher requirement | Delivery and check | Status |
|---|---|---|
| Data-flow diagram with every trust boundary | `session03/project1/data_flow.svg` and `.png`; 21 numbered flows; TB1-TB7, including the teacher Compose file's root container to Docker host (TB6) and published DB port (TB7); visually reviewed | Complete |
| At least one threat for each STRIDE letter | `risks.csv`: S, T, R, I, D, E all covered by 18 risks; each row lists its flow IDs and every flow, including 13-14, appears in a row | Complete |
| Rate every threat by likelihood x impact | All 18 numerical scores recomputed; method and assumptions stated | Complete |
| Top three risks, each with a fix | R01 (25), R02 (25), R15 (25); R03 (20) follows; fixes and acceptance checks in `REPORT.md` and PDF | Complete |
| Three-minute group presentation | Two-speaker timed outline in `PRESENTATION-3min.md` | Prepared |

The original application at commit `8d5916436b7516547898b17fc856a54807b3638f`
is preserved under `session03/project1/baseline/`. The risk analysis uses its
original `docker-compose.yml`; `compose.lab.yml` was only the local run overlay. Code/line references in the risk
report resolve inside that snapshot; they do not point at today's changed application.
The local containment overlay is included and has a SHA-256 manifest.
The report proposes fixes for the baseline; it does not claim that every planted flaw was fixed.

## C3 - Session 03, actual PDF page 30

| Teacher requirement / practical acceptance | Delivery and check | Status |
|---|---|---|
| Encrypt the NotesApp comment column with AES-GCM | Default `web/app.py` plus `web/comment_crypto.py`; AES-256-GCM, random 12-byte nonces, row-ID AAD | Passed |
| Keep existing comments readable | Transactional startup migration; 60/60 comments encrypted in each existing environment; logical before/after digests equal | Passed |
| Encrypt new and updated comments | Teacher create/update tests check stored ciphertext and exact decrypted values | Passed |
| Preserve pages, API, CSV | Student/teacher views, note API and both CSV paths tested | Passed |
| Reject modified data and wrong keys | Changed nonce/ciphertext/tag, wrong key and wrong row rejected; generic errors | Passed |
| Keep key out of source and DB | App reads `NOTESAPP_COMMENT_KEY`; launcher uses a persistent separate key volume; DB has no key mount | Passed |
| One usable application | Default app includes C3 and C4; old 8083 entry point delegates to the same implementation | Complete |

The additional Class 3 Caesar and ECB/GCM exercises retain their original code, image,
and measured results in `session03/`; they were already completed and are included.

## C4 - Class 4, actual PPTX slides 32-34 (printed 13/25)

| Teacher requirement / classroom audit criterion | Delivery and check | Status |
|---|---|---|
| HMAC in the downloaded file | Actual `/export.csv` ends in `# HMAC: ...`, covering the exact CSV bytes | Passed |
| Detect changing grade 14 to 18 | Original passes; changed file fails in the server verifier | Passed |
| Server-secret key; classroom audit flags local-only key loading | `CsvIntegrity.from_environment()` reads `NOTESAPP_CSV_HMAC_KEY`; the launcher injects the existing persistent key into env | Passed |
| Preserve previous exports | Samples signed before integration verify with the existing persistent key afterwards | Passed |
| Valid CSV, filtered exports, bad uploads and role gates | 18 HMAC checks per existing environment | Passed |

The original deck does not name a required environment-variable spelling. The env
reader additionally addresses the key-loading concern shown in the classroom audit photo.
HMAC provides integrity/authenticity under the server key, not confidentiality or non-repudiation.

## Reproduction and evidence

See the root `README.md` for fresh-install and existing-environment commands.
For either web container, run:

```bash
python runtime.py python -m unittest test_comment_encryption test_csv_integrity test_key_config test_password_storage -v
```

Set `NOTESAPP_RUN_APP_TESTS=1` in the exec environment. Each existing environment
passed **45 checks**: 17 AES, 18 HMAC, 5 key configuration, and 5 existing Argon2 regression.
These tests clean up temporary notes/accounts. Existing rows and user data are preserved.
Details: `session03/results/p1-c3-c4-verification.json`.

Fresh-install package check: **passed**. The archive was extracted to a clean directory, started with the documented default Compose command, and passed all 45 checks. Actual HTTP teacher login and a 60-row readable signed CSV export succeeded; the original upload returned 200 and a modified upload returned 400. The tested executable-source hashes are recorded in the JSON evidence.
The ZIP excludes environment files, runtime keys, local database dumps and browser captures.
