"""Local CSV validation without printing user identities or discussion text."""

import argparse
from pathlib import Path

from reddit_communities.errors import AnalysisError
from reddit_communities.ingestion import ingest_csv

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    options = parser.parse_args()
    try:
        dataset = ingest_csv(options.dataset.read_bytes(), options.dataset.name)
    except AnalysisError as error:
        parser.exit(1, f"{error.code}: {error.message}\n")
    print(dataset.quality.model_dump_json(indent=2))
