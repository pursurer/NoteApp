# Class 8 - IDOR fix (NotesApp flaw #7 closed)

**Student:** HAOJIE SONG (2023905496)

```text
IDOR FIX — NotesApp flaw #7 (broken access control) closed
  Proof you got in:   as alice, /api/notes/3 returned bob's grade: 12.6
                      Comment: "Solid work, keep it up."
  Fix:                api_notes refuses a note whose student_id is not the caller's,
                      unless the caller is a teacher/admin
  Code chosen:        returns  [x] 404 not found   [ ] 403 forbidden
  Proof it's closed:  as alice, /api/notes/3   -> 404 {"error":"not found"}
                      as alice, /api/notes/1   -> 200, alice's grade 16.2
                        Comment: "Late submission, but good quality."
                      as prof.turing, /api/notes/3 -> 200, bob's grade 12.6
                        Comment: "Solid work, keep it up."
```

The fixed `api_notes` function in [`web/app.py`](../web/app.py):

```python
@app.route("/api/notes/<int:note_id>")
def api_notes(note_id):
    ident = current_identity()
    if not ident:
        return jsonify({"error": "unauthorized"}), 401
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT n.id, n.student_id, n.class_id, n.grade, n.comment, "
        "u.username AS student, c.name AS class_name "
        "FROM notes n JOIN users u ON u.id = n.student_id "
        "JOIN classes c ON c.id = n.class_id WHERE n.id = %s",
        (note_id,),
    )
    note = cur.fetchone()
    conn.close()
    if not note:
        return jsonify({"error": "not found"}), 404

    # Flaw #7 fix: you may only read your OWN note.
    # Teachers and admins are allowed to read any note; a student is not.
    if note["student_id"] != ident["user_id"] and ident.get("role") not in ("teacher", "admin"):
        return jsonify({"error": "not found"}), 404

    note["comment"] = COMMENT_CIPHER.decrypt(note["id"], note["comment"])
    note["grade"] = float(note["grade"]) if note["grade"] is not None else None
    return jsonify(note)
```

404 is used for both a missing note and another student's note, so the response
does not confirm whether that id exists.

Source: [Class 8 lab — Read anyone's grade, then lock the door](https://kristenpire.github.io/epita-security-labs/class8/read-anyones-grade/).
