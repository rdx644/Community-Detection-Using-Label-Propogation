"""Generate the reviewable HTTP schema consumed by the TypeScript generator."""

import json
from pathlib import Path

from reddit_communities.api import create_app

if __name__ == "__main__":
    destination = Path(__file__).resolve().parents[1] / "docs/openapi.json"
    destination.write_text(json.dumps(create_app().openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"Generated {destination.name}")
