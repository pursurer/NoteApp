"""Compatibility entry point; the implementation is in web/test_comment_encryption.py."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))
import runpy
if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent.parent / "web/test_comment_encryption.py"), run_name="__main__")
else:
    from test_comment_encryption import CipherTests, AppTests
