"""Install the exact release source into an isolated workspace and test it from scratch."""

import json
import os
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from reddit_communities.exports import atomic_write

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    sandbox = ROOT / ".release-check"
    sandbox.mkdir(exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix="install-", dir=sandbox))
    names = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
        )
        .decode()
        .split("\0")
    )
    for name in sorted(set(names) - {""}):
        source = ROOT / name
        if source.is_file():
            target = workspace / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    uv = shutil.which("uv")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    assert uv and npm
    commands = [
        ([uv, "sync", "--frozen"], workspace),
        ([uv, "run", "--frozen", "pytest", "-q"], workspace),
        ([npm, "ci", "--no-audit", "--fund=false"], workspace / "frontend"),
        ([npm, "run", "build"], workspace / "frontend"),
        ([npm, "test"], workspace / "frontend"),
        ([uv, "run", "--frozen", "python", "scripts/smoke_test.py"], workspace),
    ]
    logs = []
    for command, directory in commands:
        print("Fresh install: " + " ".join(command[1:]), flush=True)
        response = subprocess.run(
            command,
            cwd=directory,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=240,
        )
        logs.append("COMMAND " + " ".join(command[1:]) + "\n" + response.stdout + response.stderr)
        atomic_write(ROOT / "artifacts/verification/fresh-install.log", "\n".join(logs).encode())
        if response.returncode:
            raise RuntimeError(f"Clean environment gate failed: {' '.join(command[1:])}")
    report = {
        "passed": True,
        "recorded_at": datetime.now(UTC).isoformat(),
        "workspace": str(workspace.relative_to(ROOT)),
        "checks": [
            "new Python venv from uv.lock",
            "complete pytest suite",
            "new Node install from package-lock",
            "typed production build",
            "frontend workflow tests",
            "native production HTTP worker + exports",
        ],
    }
    atomic_write(
        ROOT / "artifacts/verification/fresh-install.json",
        (json.dumps(report, indent=2) + "\n").encode(),
    )
    print(json.dumps(report, indent=2))
