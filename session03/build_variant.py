"""Legacy command: C3 is now part of web/app.py; no second app is generated."""
from pathlib import Path
source = (Path(__file__).resolve().parent.parent / "web/app.py").read_text()
assert "COMMENT_CIPHER = CommentCipher.from_environment()" in source
assert "CSV_INTEGRITY = CsvIntegrity.from_environment()" in source
print("C3 and C4 use the canonical web/app.py. No variant generation is needed.")
