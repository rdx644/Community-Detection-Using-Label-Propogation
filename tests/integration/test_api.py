import csv
import io
import time
import uuid
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from reddit_communities.api import create_app
from reddit_communities.config import DEFAULT_LIMITS


@pytest.fixture
def client():
    with TestClient(create_app()) as client:
        yield client


@pytest.fixture
def owner():
    return {"X-Session-ID": str(uuid.uuid4())}


def upload(client, owner, csv_bytes, **kwargs):
    return client.post(
        "/api/v1/datasets",
        headers=owner,
        files={"file": ("input.csv", csv_bytes, "text/csv")},
        **kwargs,
    )


def wait_for_run(client, owner, identifier):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/runs/{identifier}", headers=owner)
        response.raise_for_status()
        view = response.json()
        if view["status"] not in {"queued", "running"}:
            return view
        time.sleep(0.05)
    pytest.fail("Worker failed to complete within test deadline")


def test_http_full_workflow_exports_and_owner_isolation(client, owner, sample_bytes):
    assert client.get("/api/v1/health").json()["status"] == "ready"
    assert client.get("/api/v1/sample").content == sample_bytes
    response = upload(client, owner, sample_bytes)
    assert response.status_code == 201
    dataset_id = response.json()["dataset_id"]
    assert "synthetic_" not in response.text
    config = {"minimum_weight": 0.1}
    preview = client.post(f"/api/v1/datasets/{dataset_id}/preview", headers=owner, json=config)
    assert preview.json()["nodes"] == 48 and preview.json()["edges"] == 267
    response = client.post(
        "/api/v1/runs", headers=owner, json={"dataset_id": dataset_id, "config": config}
    )
    assert response.status_code == 202
    run_id = response.json()["run_id"]
    view = wait_for_run(client, owner, run_id)
    assert view["status"] == "success"
    result = view["result"]
    assert result["metrics"]["communities"] == 4
    assert result["run_id"] == run_id
    csv_response = client.get(f"/api/v1/runs/{run_id}/exports/memberships.csv", headers=owner)
    rows = list(csv.DictReader(io.StringIO(csv_response.text)))
    assert {row["user_id"]: row["community_id"] for row in rows} == result["memberships"]
    assert client.get(f"/api/v1/runs/{run_id}/exports/result.json", headers=owner).json() == result
    assert run_id in client.get(f"/api/v1/runs/{run_id}/exports/report.md", headers=owner).text
    other = {"X-Session-ID": str(uuid.uuid4())}
    for method, path, body in [
        ("get", f"/api/v1/runs/{run_id}", None),
        ("get", f"/api/v1/runs/{run_id}/exports/result.json", None),
        ("delete", f"/api/v1/datasets/{dataset_id}", None),
        ("post", f"/api/v1/datasets/{dataset_id}/preview", {}),
    ]:
        assert client.request(method, path, headers=other, json=body).status_code == 404
    assert client.get(f"/api/v1/runs/{run_id}/exports/unsafe.exe", headers=owner).status_code == 400
    assert client.delete(f"/api/v1/datasets/{dataset_id}", headers=owner).status_code == 204
    assert client.get(f"/api/v1/runs/{run_id}", headers=owner).json()["result"] == result
    assert client.delete(f"/api/v1/runs/{run_id}", headers=owner).status_code == 204
    assert client.get(f"/api/v1/runs/{run_id}", headers=owner).status_code == 404


def test_safe_errors_mapping_and_configuration(client, owner, sample_bytes):
    response = upload(client, owner, sample_bytes.replace(b"source_user", b"author", 1))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "MISSING_COLUMNS"
    assert response.headers["X-Request-ID"] == response.json()["request_id"]
    response = upload(
        client,
        owner,
        sample_bytes.replace(b"source_user", b"author", 1),
        data={"mapping": '{"author":"source_user"}'},
    )
    assert response.status_code == 201
    for mapping in ("[]", "bad", '{"author":42}'):
        assert upload(client, owner, sample_bytes, data={"mapping": mapping}).status_code == 400
    assert upload(client, {}, sample_bytes).status_code == 422
    assert (
        client.post(
            "/api/v1/runs",
            headers=owner,
            json={"dataset_id": response.json()["dataset_id"], "config": {"seed": -1}},
        ).status_code
        == 422
    )
    error = client.post(
        "/api/v1/runs",
        headers=owner,
        json={"dataset_id": "missing", "config": {"seed": "private-secret-value"}},
    )
    assert "private-secret-value" not in error.text
    assert "Traceback" not in error.text


def test_security_headers_and_cors(client):
    response = client.get("/api/v1/health", headers={"Origin": "https://untrusted.example"})
    assert "access-control-allow-origin" not in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_request_stream_and_file_limits(owner, sample_bytes):
    app = create_app(replace(DEFAULT_LIMITS, upload_bytes=100))
    with TestClient(app) as client:
        assert upload(client, owner, sample_bytes).status_code == 413

        def stream():
            yield b"x" * 50_000
            yield b"x" * 50_000

        response = client.post("/api/v1/datasets", headers=owner, content=stream())
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "REQUEST_LIMIT"


def test_timeout_failure_and_success_preservation(owner, sample_bytes):
    app = create_app(replace(DEFAULT_LIMITS, timeout_seconds=0.001))
    with TestClient(app) as client:
        dataset_id = upload(client, owner, sample_bytes).json()["dataset_id"]
        response = client.post("/api/v1/runs", headers=owner, json={"dataset_id": dataset_id})
        run_id = response.json()["run_id"]
        view = wait_for_run(client, owner, run_id)
        assert view["status"] == "failed" and view["error"]["code"] == "TIMEOUT"
        assert (
            client.get(f"/api/v1/runs/{run_id}/exports/result.json", headers=owner).status_code
            == 409
        )


def test_cancel_real_job(client, owner, sample_bytes):
    dataset_id = upload(client, owner, sample_bytes).json()["dataset_id"]
    identifier = client.post("/api/v1/runs", headers=owner, json={"dataset_id": dataset_id}).json()[
        "run_id"
    ]
    assert client.delete(f"/api/v1/runs/{identifier}", headers=owner).status_code == 204
    assert wait_for_run(client, owner, identifier)["status"] == "cancelled"


def test_retention_cleanup_without_followup_request(owner, sample_bytes):
    app = create_app(replace(DEFAULT_LIMITS, retention_seconds=0.05))
    with TestClient(app) as client:
        assert upload(client, owner, sample_bytes).status_code == 201
        deadline = time.monotonic() + 3
        while app.state.service.datasets and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not app.state.service.datasets
