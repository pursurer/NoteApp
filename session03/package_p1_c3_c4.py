"""Create a reproducible source package from coursework files, never runtime data."""

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


APP = Path(__file__).resolve().parent.parent
OUT = APP.parent / "output"


def main():
    files = {}

    def add(path, name):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Expected a regular coursework file: {path}")
        if any(part in {"instance", "certs", "__pycache__", ".venv", ".git"}
               or part.startswith(".env") for part in path.parts):
            raise ValueError("Runtime files are excluded.")
        if path.suffix.lower() in {".key", ".pem", ".dump", ".pcap", ".pcapng", ".pyc"}:
            raise ValueError("Keys, databases, and captures are excluded.")
        data = path.read_bytes()
        if name == "NoteApp/README.md":
            text = data.decode()
            start = text.index("Class 5 HTTP capture")
            end = text.index("## P1, C3 and C4 delivery", start)
            text = text[:start] + "This package contains P1, C3 and C4. C5 reports remain in the full working copy.\n\n" + text[end:]
            start = text.index("For the existing local HTTPS environment:")
            end = text.index("The historic C3 entry point", start)
            text = text[:start] + text[end:]
            data = text.encode()
        files[name] = data

    for name in ("README.md", "P1-C3-C4-REQUIREMENTS.md", ".gitignore", ".dockerignore",
                 "docker-compose.yml", "compose.lab.yml", "compose.session03.yml", "db/init.sql"):
        add(APP / name, "NoteApp/" + name)
    for folder in ("web", "session03", "session04"):
        for path in sorted((APP / folder).rglob("*")):
            if not path.is_file() or any(p in {"__pycache__", ".venv", "instance"} for p in path.parts):
                continue
            if path.suffix.lower() not in {".py", ".md", ".json", ".csv", ".svg", ".png", ".html", ".css", ".txt", ".bin", ".diff", ".yml"} and path.name not in {"Dockerfile", ".dockerignore"}:
                continue
            add(path, "NoteApp/" + str(path.relative_to(APP)))
    for name in ("Session03-Lab-and-Homework.pdf", "Session03-Project1-Risk-Analysis.pdf"):
        add(OUT / "pdf" / name, "reports/" + name)
    files["START-HERE.md"] = b"""# P1, C3 and C4 coursework

P1 group: ZIQIAN YU (2023902046); HAOJIE SONG (2023905496).
Read reports/Session03-Project1-Risk-Analysis.pdf and NoteApp/P1-C3-C4-REQUIREMENTS.md.

From NoteApp/, run: docker compose up -d --build --wait
Open http://127.0.0.1:8080. Use the demo accounts in NoteApp/README.md.
C3 and C4 are in the default web/app.py. Startup generates new, independent local keys
and migrates the included demo data. A new installation cannot verify exports signed by
another installation's key; download a new CSV in that installation for the demonstration.

The package includes source, demo seed data, reports, tests, and aggregate verification.
It excludes private keys, local databases, browser captures, and environment files.
"""
    manifest = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}
    files["SHA256-MANIFEST.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    OUT.mkdir(exist_ok=True)
    target = OUT / "P1-C3-C4-Submission.zip"
    with ZipFile(target, "w", ZIP_DEFLATED, compresslevel=6) as z:
        for name, data in sorted(files.items()):
            z.writestr(name, data)
    with ZipFile(target) as z:
        if z.testzip() is not None:
            raise ValueError("Archive integrity check failed.")
        for name, expected in manifest.items():
            if hashlib.sha256(z.read(name)).hexdigest() != expected:
                raise ValueError("Archive hash mismatch.")
    print(json.dumps({"archive": str(target), "files": len(files),
                      "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                      "manifest_verified": True, "runtime_keys_included": False}, indent=2))


if __name__ == "__main__":
    main()
