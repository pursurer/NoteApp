"""Load stable keys into the child environment; migrate before serving requests."""

import os
import sys

from key_config import load_environment


def main():
    load_environment()
    command = sys.argv[1:]
    if command and command[0] == "--migrate":
        from migrate_comments import main as migrate
        migrate()
        command = command[1:]
    if not command:
        raise SystemExit("Pass the application or verification command.")
    sys.stdout.flush()
    os.execvpe(command[0], command, os.environ)


if __name__ == "__main__":
    main()
