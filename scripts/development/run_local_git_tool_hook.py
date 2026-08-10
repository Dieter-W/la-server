"""Run optional local hooks from .git-tools/ (skipped when the script is missing)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GIT_TOOLS_DIR = PROJECT_ROOT / ".git-tools"


def run_local_hook(script_name: str, extra_args: list[str]) -> int:
    hook_path = GIT_TOOLS_DIR / script_name
    if not hook_path.is_file():
        return 0

    result = subprocess.run(
        [sys.executable, str(hook_path), *extra_args],
        cwd=PROJECT_ROOT,
        check=False,
    )
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "hook_script",
        help="filename inside .git-tools/ (e.g. local-pre-commit-hook.py)",
    )
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="arguments forwarded to the local hook script",
    )
    args = parser.parse_args()
    return run_local_hook(args.hook_script, args.args)


if __name__ == "__main__":
    sys.exit(main())
