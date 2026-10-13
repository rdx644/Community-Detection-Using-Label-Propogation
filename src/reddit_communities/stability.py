"""Label-invariant, pairwise adjusted Rand index for seeded partitions."""

from collections import Counter
from itertools import combinations
from math import comb

import networkx as nx

from .errors import AnalysisError
from .lpa_engine import detect_communities
from .schemas import SeedComparison, StabilityResult


def adjusted_rand_index(first: dict[str, str], second: dict[str, str]) -> float:
    if set(first) != set(second):
        raise AnalysisError("PARTITION_MISMATCH", "Stability partitions must share the same nodes")
    if len(first) < 2:
        return 1.0
    cells = Counter((first[node], second[node]) for node in sorted(first))
    a = sum(comb(count, 2) for count in Counter(first.values()).values())
    b = sum(comb(count, 2) for count in Counter(second.values()).values())
    agreement = sum(comb(count, 2) for count in cells.values())
    expected = a * b / comb(len(first), 2)
    denominator = (a + b) / 2 - expected
    return (agreement - expected) / denominator if denominator else 1.0


def compare_seeds(graph: nx.Graph, seeds: list[int], weighted: bool) -> StabilityResult:
    partitions = {seed: detect_communities(graph, seed, weighted) for seed in seeds}
    comparisons = [
        SeedComparison(
            seed_a=a,
            seed_b=b,
            adjusted_rand_index=adjusted_rand_index(partitions[a], partitions[b]),
        )
        for a, b in combinations(seeds, 2)
    ]
    return StabilityResult(
        seeds=seeds,
        comparisons=comparisons,
        mean_ari=sum(item.adjusted_rand_index for item in comparisons) / len(comparisons)
        if comparisons
        else None,
    )
