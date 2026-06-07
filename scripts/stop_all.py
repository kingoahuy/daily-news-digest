import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    exit_code = 0
    for script in ("stop_frontend.py", "stop_web.py"):
        completed = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / script)],
            cwd=PROJECT_ROOT,
            check=False,
        )
        exit_code = max(exit_code, completed.returncode)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
