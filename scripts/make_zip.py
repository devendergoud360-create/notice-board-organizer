"""Create a clean submission ZIP from all git-tracked files.

Excludes forbidden folders/files and verifies parity with `git ls-files`.
"""

from __future__ import annotations

import os
import subprocess
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(ROOT), "notice-board-organizer-submission.zip")

FORBIDDEN_PARTS = {
    "node_modules", "venv", ".venv", "__pycache__", ".git", "build", "dist"
}
FORBIDDEN_SUFFIX = (".pyc", ".pyo", ".log", ".tmp", ".bak")


def tracked_files() -> list[str]:
    out = subprocess.check_output(
        ["git", "ls-files"], cwd=ROOT, text=True
    ).strip().splitlines()
    return [f for f in out if f]


def is_allowed(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    if any(p in FORBIDDEN_PARTS for p in parts):
        return False
    if rel.endswith(FORBIDDEN_SUFFIX):
        return False
    return True


def main() -> None:
    tracked = tracked_files()
    included = [f for f in tracked if is_allowed(f)]
    excluded = [f for f in tracked if not is_allowed(f)]

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in included:
            zf.write(os.path.join(ROOT, rel), rel)

    print(f"ZIP: {OUT}")
    print(f"Tracked files: {len(tracked)}")
    print(f"Included in ZIP: {len(included)}")
    print(f"Excluded (forbidden): {len(excluded)}")
    for f in excluded:
        print(f"  - {f}")
    with zipfile.ZipFile(OUT) as zf:
        names = set(zf.namelist())
    missing = [f for f in included if f not in names]
    print(f"Missing from ZIP: {len(missing)}")
    if missing:
        for f in missing:
            print(f"  ! {f}")
        raise SystemExit(1)
    print("AUDIT OK: clean ZIP contains every allowed git-tracked file.")


if __name__ == "__main__":
    main()
