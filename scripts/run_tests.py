from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str]) -> int:
    target = argv[1] if len(argv) > 1 else "tests"
    cmd = [
        sys.executable, "-m", "pytest", "-q", "--tb=line", str(target),
    ]
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))