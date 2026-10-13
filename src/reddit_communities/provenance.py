"""Dataset-scoped pseudonyms and traceable reproducibility metadata."""

import hashlib
import json
import platform
from datetime import UTC, datetime

import networkx as nx

from . import __version__
from .schemas import Provenance, ValidatedDataset


def pseudonym(user: str, fingerprint: str) -> str:
    return "user_" + hashlib.sha256((fingerprint + "\0" + user).encode()).hexdigest()[:20]


def create_provenance(dataset: ValidatedDataset, memberships: dict[str, str]) -> Provenance:
    encoded = json.dumps(memberships, sort_keys=True, separators=(",", ":")).encode()
    return Provenance(
        dataset_sha256=dataset.fingerprint,
        membership_sha256=hashlib.sha256(encoded).hexdigest(),
        created_at=datetime.now(UTC),
        python_version=platform.python_version(),
        networkx_version=nx.__version__,
        application_version=__version__,
        input_columns=list(dataset.columns),
        column_mapping=dict(dataset.mapping),
    )
