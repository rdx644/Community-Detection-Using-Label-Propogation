# Researcher guide

1. Start the app using README commands and open Data import. Choose a CSV or the
   clearly marked synthetic sample. You can download the sample without importing it.
2. Review schema errors. For alternate field names, map source headers to each canonical
   field and validate again. Fatal malformed CSV does not reach graph construction.
3. Review input/accepted/quarantined/duplicate/self-loop counts and rejection reasons.
   Quarantine reasons are bounded to 50. Validated uploads can be deleted explicitly.
4. Open Configure. Set seed, minimum aggregated edge weight, UTC window, interaction
   types, subreddit, weighted/unweighted mode and largest-component policy. Preview the
   graph to see exact counts before running. Stability compares up to five distinct seeds;
   an empty seed list skips it. Invalid configuration gets an actionable error.
5. Run detection. Loading status reflects a real job. Cancel stops the worker; previous
   successful results remain selectable. A timeout fails safely without overwriting them.
6. Explore. Select a community or a node, zoom, search dataset-scoped pseudonymous IDs,
   and filter minimum members or discussion context. These display filters do not change
   saved metrics. Rerun the analytical configuration to change the underlying graph.
   Up to 400 nodes and 1,500 edges are shown; the first 100 community buttons are shown
   for very large partitions. Full memberships and metrics are always in exports.
7. Evaluation explains modularity, sizes, internal edges, runtime, seed agreement,
   pipeline accounting and warnings. Undefined metrics are shown as a dash/explicit
   undefined value. Subreddit context is not verified expertise or text topic coherence.
8. Export CSV memberships, complete JSON and a Markdown report. Verify the run ID and
   dataset hash when combining artifacts. Delete saved runs when no longer needed.

Uploads/results expire after 30 minutes; server restarts and browser-page reloads lose
the interactive workspace. The browser's session token persists across page reloads,
but the UI does not restore old run references automatically. Keep downloaded artifacts.
Use public data consistent with your research/data-source obligations. This application
does not collect data from Reddit or contact users.

For reproduction use exactly the original bytes, saved config, Python 3.12 and locked
dependencies. Byte-identical sample CSVs are preserved by `.gitattributes`. Compare
membership hashes, not run IDs/timestamps/runtime, which change on every execution.
Layout coordinates are a deterministic community-group display, not graph-distance evidence.
