"""Reproducible real-browser gate using explicit Playwright CLI actions and snapshots."""

import csv
import io
import json
import os
import re
import subprocess
import time
from pathlib import Path

from benchmark import benchmark_data
from smoke_test import production_server

from reddit_communities.exports import atomic_write

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
EXECUTABLE = (
    FRONTEND / "node_modules/.bin" / ("playwright-cli.cmd" if os.name == "nt" else "playwright-cli")
)
SESSION = "phase-gate"
logs: list[str] = []


def cli(*arguments: str) -> str:
    response = subprocess.run(
        [str(EXECUTABLE), f"-s={SESSION}", *arguments],
        cwd=FRONTEND,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=45,
    )
    logs.append("COMMAND " + " ".join(arguments) + "\n" + response.stdout + response.stderr)
    if response.returncode:
        raise RuntimeError(f"Browser CLI failed: {arguments[0]}")
    return response.stdout


def control(role: str, name: str, index: int = 0) -> str:
    snapshot = cli("snapshot")
    matches = [
        reference
        for text, reference in re.findall(rf'{role} "([^"\n]+)"[^\n]*\[ref=(e\d+)\]', snapshot)
        if name in text
    ]
    if len(matches) <= index:
        raise AssertionError(f"Missing visible {role}: {name}")
    return matches[index]


def click(name: str, index: int = 0) -> None:
    cli("click", control("button", name, index))


def wait_for(text: str) -> str:
    deadline = time.monotonic() + 65
    while time.monotonic() < deadline:
        snapshot = cli("snapshot")
        if text in snapshot:
            return snapshot
        time.sleep(0.25)
    raise AssertionError(f"Browser deadline waiting for {text}")


def verify(url: str) -> dict[str, object]:
    cli("open", url)
    cli("resize", "1440", "1000")
    click("Explore the synthetic sample")
    wait_for("Data quality report")
    click("Configure analysis")
    cli("fill", control("spinbutton", "Minimum edge weight"), "0.1")
    click("Preview graph")
    wait_for('heading "Graph preview"')
    click("Run detection", 1)
    wait_for("Interaction communities")
    snapshot = wait_for("Interaction edges: 267")
    assert "Eligible users: 48" in snapshot and "Detected communities: 4" in snapshot
    cli("set-reduced-motion", "reduce")
    cli("press", "Control+Home")
    cli("screenshot", "--filename=../output/playwright/explorer-desktop.png")
    click("C001 12 members")
    cli("fill", control("spinbutton", "Minimum community size"), "13")
    snapshot = cli("snapshot")
    assert "0 shown / 48 total nodes" in snapshot and "0 visible edges" in snapshot
    cli("fill", control("spinbutton", "Minimum community size"), "1")
    click("Evaluation")
    assert "Mean pairwise ARI" in cli("snapshot").replace("MEAN PAIRWISE ARI", "Mean pairwise ARI")
    click("Export")
    before = set((FRONTEND / ".playwright-cli").glob("*-result.json"))
    click("Download csv")
    click("Download json")
    click("Download markdown")
    exported = set((FRONTEND / ".playwright-cli").glob("*-result.json")) - before
    assert len(exported) == 1
    result = json.loads(exported.pop().read_text(encoding="utf-8"))
    run_id = result["run_id"]
    csv_path = FRONTEND / ".playwright-cli" / f"{run_id}-memberships.csv"
    rows = list(csv.DictReader(io.StringIO(csv_path.read_text(encoding="utf-8"))))
    assert {row["user_id"]: row["community_id"] for row in rows} == result["memberships"]
    assert run_id in (FRONTEND / ".playwright-cli" / f"{run_id}-report.md").read_text(
        encoding="utf-8"
    )
    cli("resize", "390", "844")
    cli("press", "Control+Home")
    cli("screenshot", "--filename=../output/playwright/export-mobile.png")
    click("Data import")
    click("Choose CSV file")
    invalid = ROOT / "output/playwright/invalid.csv"
    invalid.write_text("wrong,headers\na,b\n", encoding="utf-8")
    cli("upload", str(invalid))
    wait_for("Map your column names")
    assert "synthetic_sample_interactions.csv" in cli("snapshot")
    mapped = ROOT / "output/playwright/mapped.csv"
    mapped.write_text(
        (ROOT / "data/sample/sample_interactions.csv")
        .read_text(encoding="utf-8")
        .replace("source_user", "author", 1),
        encoding="utf-8",
    )
    click("Choose CSV file")
    cli("upload", str(mapped))
    wait_for("Map your column names")
    cli("select", control("combobox", "Map source_user"), "author")
    click("Validate mapped CSV")
    snapshot = wait_for("Validation complete")
    assert "mapped.csv" in snapshot
    console = cli("console", "error")
    error_lines = [line for line in console.splitlines() if line.startswith("[ERROR]")]
    assert len(error_lines) == 2 and all(
        "status of 422" in line and "/api/v1/datasets" in line for line in error_lines
    ), "Expected only the two deliberate schema-validation HTTP failures"
    # Exercise the declared benchmark through the browser, including bounded SVG rendering.
    large = ROOT / "output/playwright/benchmark.csv"
    large.write_bytes(benchmark_data())
    click("Choose CSV file")
    cli("upload", str(large))
    wait_for("Validation complete")
    click("Configure analysis")
    click("Run detection")
    snapshot = wait_for("400 shown / 1000 total nodes")
    edge_match = re.search(r"(\d+) visible edges", snapshot)
    assert edge_match and 0 < int(edge_match.group(1)) <= 1500 and "Summary view" in snapshot
    visible_edges = int(edge_match.group(1))
    started = time.perf_counter()
    click("C001 100 members")
    assert 'heading "Patterns of interaction"' in cli("snapshot")
    interaction_seconds = time.perf_counter() - started
    return {
        "gate": "real browser",
        "passed": True,
        "viewport_checks": ["1440x1000", "390x844"],
        "sample_metrics": result["metrics"],
        "large_graph": {
            "total_nodes": 1000,
            "visible_nodes": 400,
            "visible_edges": visible_edges,
            "community_selection_cli_wall_seconds": interaction_seconds,
            "timing_note": "includes CLI startup and snapshots, not pure render time",
        },
        "checks": [
            "sample validation",
            "configuration",
            "graph preview",
            "real LPA",
            "community selection",
            "empty filter + visible edge count",
            "evaluation",
            "three downloads + roundtrip",
            "mobile layout",
            "invalid input recovery",
            "previous dataset label preserved",
            "mapped upload",
            "browser console",
            "reduced-motion accessibility",
            "benchmark upload + bounded graph interaction",
        ],
    }


if __name__ == "__main__":
    evidence_dir = ROOT / "artifacts/verification"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    try:
        with production_server() as url:
            evidence = verify(url)
        atomic_write(
            evidence_dir / "browser-gate.json", (json.dumps(evidence, indent=2) + "\n").encode()
        )
        print(json.dumps(evidence, indent=2))
    finally:
        cli("close")
        atomic_write(ROOT / "output/playwright/browser-gate.log", "\n".join(logs).encode())
