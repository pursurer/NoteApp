"""Compatibility entry point; the implementation is in web/migrate_comments.py."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))
from migrate_comments import main
if __name__ == "__main__":
    main()
