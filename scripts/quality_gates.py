"""Execute the release checks with recorded exit codes; any failing command blocks push."""

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from reddit_communities.exports import atomic_write

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    uv = shutil.which("uv")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    assert uv and npm
    checks = [
        ([uv, "run", "ruff", "check", "."], ROOT),
        ([uv, "run", "ruff", "format", "--check", "."], ROOT),
        ([uv, "run", "mypy"], ROOT),
        ([uv, "run", "pytest", "-q"], ROOT),
        ([uv, "run", "python", "scripts/scan_secrets.py"], ROOT),
        ([uv, "run", "pip-audit", "-r", "requirements.lock"], ROOT),
        ([npm, "run", "format:check"], ROOT / "frontend"),
        ([npm, "run", "lint"], ROOT / "frontend"),
        ([npm, "test"], ROOT / "frontend"),
        ([npm, "run", "build"], ROOT / "frontend"),
        ([npm, "audit", "--audit-level=high"], ROOT / "frontend"),
    ]
    evidence: list[dict[str, object]] = []
    for command, directory in checks:
        label = " ".join(command[1:])
        print("Gate: " + label, flush=True)
        result = subprocess.run(
            command,
            cwd=directory,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=240,
        )
        evidence.append(
            {
                "command": label,
                "directory": str(directory.relative_to(ROOT)),
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        report = {
            "recorded_at": datetime.now(UTC).isoformat(),
            "passed": result.returncode == 0,
            "checks": evidence,
        }
        atomic_write(
            ROOT / "artifacts/verification/quality-gates.json",
            (json.dumps(report, indent=2) + "\n").encode(),
        )
        if result.returncode:
            print(result.stdout + result.stderr)
            raise SystemExit(result.returncode)
    print(f"All {len(evidence)} quality gates passed")
