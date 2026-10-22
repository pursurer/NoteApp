# Class 4 - NotesApp CSV export integrity

**P1/C3/C4 group:** ZIQIAN YU (2023902046); HAOJIE SONG (2023905496).  
**Updated:** 22 October 2026.

## Required behavior

The original Class 4 deck, actual slides 32-34 (printed 13/25), requires an HMAC
inside the exported file. Changing one grade must make the check fail.

## Implementation

`web/app.py` signs the actual `/export.csv` response with HMAC-SHA256.
The complete UTF-8 CSV bytes, including the header and CRLF endings, are authenticated.
The final line is `# HMAC: <64 lowercase hex characters>` and is excluded from its own HMAC.
This is integrity protection; the CSV remains readable.

`CsvIntegrity.from_environment()` reads `NOTESAPP_CSV_HMAC_KEY`. The launcher loads
the existing private key file into the child process environment, retaining old signatures.
The HMAC key is independent of the AES comment key. Missing, malformed, or equal keys
stop startup. No key is exported in the file or included with this report.

At the teacher-only `/verify-export` page, the original file succeeds; modified,
unsigned, malformed, oversized, and differently keyed files are rejected.
Verification compares the original bytes with `hmac.compare_digest` before parsing.
The verifier does not import grades or persist an uploaded file.

## Actual verification

Both existing environments passed 18 HMAC checks, as part of 45 combined checks each.
A grade change from 14 to 18 failed verification. Both unfiltered and filtered exports
were checked. Anonymous users and students could not export or verify.
CSV samples signed before the launcher/environment change still verified afterwards.
Both environments retained 60 notes with the same logical values after integration.

C3 encrypts comments in the database and decrypts them for an authorized export.
C4 then authenticates that readable export. The default app implements both steps.

See `../P1-C3-C4-REQUIREMENTS.md` and `../session03/results/p1-c3-c4-verification.json`
for the requirement mapping and aggregate results. Remaining course authentication/authorization
flaws limit the trust of the teaching application and are documented in the pinned P1 baseline.
