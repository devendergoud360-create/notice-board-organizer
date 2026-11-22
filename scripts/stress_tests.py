"""Run the full test suite repeatedly to detect flaky tests."""

import subprocess
import sys


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    failures = 0
    for i in range(1, runs + 1):
        p = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests",
             "-p", "test_*.py"],
            capture_output=True, text=True,
        )
        ok = "FAILED" not in p.stderr and p.returncode == 0
        print(f"RUN {i}: {'OK' if ok else 'FAILED'}")
        if not ok:
            failures += 1
            for line in (p.stderr + p.stdout).splitlines():
                if any(t in line for t in ("ERROR:", "FAIL:", "Error:", "Traceback")):
                    print("   ", line)
    print(f"{runs} runs complete — failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
