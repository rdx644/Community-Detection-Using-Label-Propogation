"""Native production startup, real HTTP worker and export consistency gate."""

import csv
import io
import json
import socket
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx

from reddit_communities.exports import atomic_write

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def production_server() -> Iterator[str]:
    with socket.socket() as bound:
        bound.bind(("127.0.0.1", 0))
        port = bound.getsockname()[1]
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "reddit_communities.api:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
        ],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                if httpx.get(url + "/api/v1/health", timeout=1).is_success:
                    break
            except httpx.HTTPError:
                pass
            if process.poll() is not None:
                raise RuntimeError("Production server stopped during startup")
            time.sleep(0.1)
        else:
            raise RuntimeError("Production server startup timed out")
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def smoke(url: str) -> dict[str, object]:
    owner = {"X-Session-ID": str(uuid.uuid4())}
    with httpx.Client(base_url=url, headers=owner, timeout=10) as client:
        html = client.get("/")
        html.raise_for_status()
        assert "Community Observatory" in html.text and "/assets/" in html.text
        sample = client.get("/api/v1/sample")
        sample.raise_for_status()
        uploaded = client.post("/api/v1/datasets", files={"file": ("sample.csv", sample.content)})
        uploaded.raise_for_status()
        dataset_id = uploaded.json()["dataset_id"]
        response = client.post(
            "/api/v1/runs", json={"dataset_id": dataset_id, "config": {"minimum_weight": 0.1}}
        )
        response.raise_for_status()
        run_id = response.json()["run_id"]
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            response = client.get(f"/api/v1/runs/{run_id}")
            response.raise_for_status()
            view = response.json()
            if view["status"] not in {"queued", "running"}:
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("Smoke analysis deadline exceeded")
        assert view["status"] == "success", view.get("error")
        result = view["result"]
        assert result["metrics"]["nodes"] == 48 and result["metrics"]["communities"] == 4
        exported = client.get(f"/api/v1/runs/{run_id}/exports/result.json")
        exported.raise_for_status()
        assert exported.json() == result
        memberships = client.get(f"/api/v1/runs/{run_id}/exports/memberships.csv")
        memberships.raise_for_status()
        rows = list(csv.DictReader(io.StringIO(memberships.text)))
        assert {row["user_id"]: row["community_id"] for row in rows} == result["memberships"]
        report = client.get(f"/api/v1/runs/{run_id}/exports/report.md")
        report.raise_for_status()
        assert run_id in report.text
        assert "synthetic_" not in exported.text
        invalid = client.post("/api/v1/datasets", files={"file": ("invalid.csv", b"a,b\n1,2")})
        assert invalid.status_code == 422
        return {
            "gate": "production startup and HTTP workflow",
            "passed": True,
            "metrics": result["metrics"],
            "run_id": run_id,
            "checks": [
                "built SPA",
                "health",
                "upload",
                "real worker",
                "CSV/JSON/report",
                "export roundtrip",
                "pseudonyms",
                "invalid input recovery",
            ],
        }


if __name__ == "__main__":
    with production_server() as url:
        evidence = smoke(url)
    atomic_write(
        ROOT / "artifacts/verification/production-smoke.json",
        (json.dumps(evidence, indent=2) + "\n").encode(),
    )
    print(json.dumps(evidence, indent=2))
