"""Compatibility initializer; retain the existing AES key without printing it."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))
from key_config import persistent_key
if __name__ == "__main__":
    persistent_key(os.environ["NOTESAPP_COMMENT_KEY_FILE"])
    print("The persistent AES key is ready; its value is not shown.")
