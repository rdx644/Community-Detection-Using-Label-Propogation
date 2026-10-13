import json
from pathlib import Path

from reddit_communities.api import create_app


def test_frozen_openapi_matches_implementation():
    path = Path(__file__).resolve().parents[2] / "docs/openapi.json"
    assert json.loads(path.read_text(encoding="utf-8")) == create_app().openapi()
