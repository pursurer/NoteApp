"""Encrypt existing comments in one transaction. Verify before commit."""

import hashlib
import json
import os

import psycopg2
import psycopg2.extras

from comment_crypto import CommentCipher, PREFIX


def main():
    cipher = CommentCipher.from_environment()
    conn = psycopg2.connect(
        host=os.environ["DB_HOST"], dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"], password=os.environ["POSTGRES_PASSWORD"],
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    migrated = skipped = 0
    before = hashlib.sha256()
    after = hashlib.sha256()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("LOCK TABLE notes IN ACCESS EXCLUSIVE MODE")
                cur.execute("SELECT id, comment FROM notes ORDER BY id")
                rows = cur.fetchall()
                for row in rows:
                    stored = row["comment"]
                    if isinstance(stored, str) and stored.startswith(PREFIX):
                        plain = cipher.decrypt(row["id"], stored)
                        skipped += 1
                    else:
                        plain = stored
                        stored = cipher.encrypt(row["id"], plain)
                        cur.execute("UPDATE notes SET comment = %s WHERE id = %s",
                                    (stored, row["id"]))
                        migrated += 1
                    before.update(json.dumps([row["id"], plain], ensure_ascii=False).encode())
                cur.execute("SELECT id, comment FROM notes ORDER BY id")
                verified_rows = cur.fetchall()
                for row in verified_rows:
                    plain = cipher.decrypt(row["id"], row["comment"])
                    after.update(json.dumps([row["id"], plain], ensure_ascii=False).encode())
                if before.digest() != after.digest():
                    raise RuntimeError("The comment check failed. Roll back the transaction.")
                cur.execute("SELECT 1 FROM pg_constraint WHERE conname = %s AND conrelid = 'notes'::regclass",
                            ("notes_comment_gcm1",))
                if not cur.fetchone():
                    cur.execute("ALTER TABLE notes ADD CONSTRAINT notes_comment_gcm1 "
                                "CHECK (comment IS NOT NULL AND comment LIKE 'gcm1:%')")
        print(json.dumps({"migrated": migrated, "skipped": skipped,
                          "verified": len(verified_rows), "plaintext_digest_matches": True}))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
