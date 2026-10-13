# Data contract v1

UTF-8 (optional BOM), comma-separated `.csv`, header row; 5 MiB / 50,000 row limit.
Quoted cells may contain commas/newlines. Duplicate headers and ragged records fail.
At most 100 columns are accepted; headers are at most 128 characters.

Required columns: `source_user`, `target_user`, `interaction_type`, `timestamp`, `subreddit`.
Optional: `interaction_id`, `weight`, `post_id`, `text`. Unknown columns are ignored.
An explicit source-header → canonical-header mapping is accepted on validation.

Identifiers are case-sensitive, whitespace-trimmed nonempty strings, max 128 characters.
No case folding, Unicode normalization or inferred identity merging is performed.
`timestamp` is ISO-8601 with a timezone and normalized to UTC. Naive timestamps fail.
Types are `reply`, `mention`, `shared_discussion`; supplied pairs must represent actual
events, never mere coactivity in a subreddit. Subreddit is trimmed, max 128 characters;
an empty value is accepted as unknown. Empty optional weight defaults to 1, but a supplied
value must be finite and >0. Weight aggregation must also remain finite.

Invalid records are quarantined. Valid records are deduplicated first by nonempty
interaction_id; conflicting records with the same ID are rejected as conflicts. Without
an ID use `(source,target,type,UTC timestamp,subreddit,weight,post_id,text)` fingerprint.
Then drop self-loops. Genuine repeated events with different IDs/times remain.
Count equation: input_rows = accepted_rows + rejected_rows + duplicate_rows + self_loops.
Only the first 50 rejection reasons are returned. Fatal file/schema errors never enter
graph construction. No usable events gives an explicit error.

Preserve direction in normalized in-memory events. Filter events by inclusive UTC
window/type/subreddit, add their endpoint nodes, sum weights per sorted undirected pair,
then apply minimum weight. Unweighted mode sets remaining edge weights to 1. Nodes made
isolated by thresholding remain singleton communities. Largest-component filtering is
explicit and deterministic (size descending, lexical tie-break); removed nodes reported.

IDs in result/export are deterministic dataset-scoped SHA-256 pseudonyms (`user_` +
20 hex characters). These reduce casual exposure but are not cryptographic anonymization
against guessing. Normalized identifiers/text remain in expiring process memory. Multipart
parsing may use transient OS temporary files, closed after bounded reading; no persistent
raw dataset archive is created.

## Output formats
JSON schema generated in `docs/openapi.json`. A saved result includes schema_version,
run_id, status, memberships, communities, metrics, quality, graph summary/preview,
configuration, stability, provenance and warnings. Undefined metrics use JSON null.
CSV columns: run_id,user_id,community_id; one row per eligible node, sorted by ID.
Markdown report contains actual summary values, caveats and provenance.
CSV values beginning with =,+,-,@,tab,CR are prefixed with an apostrophe.
