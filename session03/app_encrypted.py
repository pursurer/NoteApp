"""Compatibility entry point; the implementation is in web/app.py."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))
from app import *
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8083, debug=False)
