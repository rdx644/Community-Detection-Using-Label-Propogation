# Interaction community analysis

Run: `3a824b8a-5716-4722-860e-b67c8d7dbae2`

Status: success

Nodes: 48; edges: 267; communities: 4.

Weighted modularity: 0.749542. Runtime: 0.010122 seconds.

These are interaction communities, not verified academic interests or expertise.
Subreddit context is interpreted separately from label propagation.

## Reproducibility

```json
{
  "configuration": {
    "seed": 42,
    "weighted": true,
    "minimum_weight": 0.1,
    "start_time": null,
    "end_time": null,
    "interaction_types": [
      "reply",
      "mention",
      "shared_discussion"
    ],
    "subreddits": [],
    "largest_component_only": false,
    "stability_seeds": [
      42,
      7,
      21
    ]
  },
  "provenance": {
    "dataset_sha256": "2f4c6948528f6cdbac1546025b5f8c758111733026cea766ee3caa2197be3926",
    "membership_sha256": "14c60a5c0f2e2a41f9bee0c94221efd05a2aeb4b996ec00df86d9f717f012904",
    "created_at": "2026-10-13T21:27:42.670921Z",
    "python_version": "3.12.10",
    "networkx_version": "3.7",
    "application_version": "1.0.0",
    "algorithm": "networkx.asyn_lpa_communities",
    "identifier_policy": "dataset-scoped SHA-256 pseudonyms",
    "input_columns": [
      "source_user",
      "target_user",
      "interaction_type",
      "timestamp",
      "subreddit",
      "interaction_id",
      "weight",
      "post_id",
      "text"
    ],
    "column_mapping": {},
    "preprocessing_policy": "trim IDs; UTC; event dedup; drop loops; sum pairs; keep isolates"
  },
  "quality": {
    "input_rows": 267,
    "accepted_rows": 267,
    "rejected_rows": 0,
    "duplicate_rows": 0,
    "self_loops": 0,
    "rejections": []
  }
}
```

Warnings: none
