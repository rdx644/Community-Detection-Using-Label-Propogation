"""Fail the gate on secret findings in project-owned source, never traverse dependencies."""

import json
import os
from pathlib import Path

from detect_secrets import SecretsCollection
from detect_secrets.settings import default_settings

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    os.chdir(ROOT)
    sources = ["src", "tests", "scripts", "frontend/src", "frontend/scripts", "docs", ".github"]
    files = [
        path
        for directory in sources
        for path in Path(directory).rglob("*")
        if path.is_file()
        and path.suffix in {".py", ".ts", ".tsx", ".js", ".mjs", ".json", ".md", ".yml", ".csv"}
    ]
    files += [
        Path(path) for path in ("app.py", "pyproject.toml", ".env.example", "frontend/package.json")
    ]
    collection = SecretsCollection()
    with default_settings():
        for path in sorted(files):
            collection.scan_file(str(path))
    report = {
        "scanner": "detect-secrets",
        "scanned_files": len(files),
        "results": collection.json(),
    }
    (ROOT / "artifacts/verification").mkdir(parents=True, exist_ok=True)
    (ROOT / "artifacts/verification/secret-scan.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    count = sum(len(findings) for findings in report["results"].values())
    print(f"Secret scan: {len(files)} project-owned files; {count} findings")
    raise SystemExit(1 if count else 0)
