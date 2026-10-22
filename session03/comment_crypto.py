"""Compatibility import for the canonical web comment cipher."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))
from web.comment_crypto import CommentCipher, CommentIntegrityError, PREFIX
