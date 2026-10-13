import { useMemo, useState } from "react";
import { Maximize2, Minus, Plus, Search } from "lucide-react";
import type { AnalysisResult } from "../types";

export const palette = [
  "#c9df94",
  "#8bc3cd",
  "#e9ac89",
  "#b5a8d1",
  "#e6cc7c",
  "#89c0ac",
];
export function communityColor(id: string) {
  return palette[(Number(id.slice(1)) - 1) % palette.length] ?? palette[0];
}
export function NetworkGraph({
  result,
  selected,
  onSelect,
}: {
  result: AnalysisResult;
  selected: string;
  onSelect: (id: string) => void;
}) {
  const [search, setSearch] = useState("");
  const [zoom, setZoom] = useState(1);
  const [nodeID, setNodeID] = useState("");
  const nodes = useMemo(
    () => new Map(result.graph.nodes.map((node) => [node.id, node])),
    [result],
  );
  const matches = Object.keys(result.memberships).filter(
    (id) => search && id.toLowerCase().includes(search.toLowerCase()),
  );
  const current = nodes.get(nodeID);
  return (
    <section className="panel network-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">NETWORK VIEW</span>
          <h2>Patterns of interaction</h2>
        </div>
        <span className="pill">
          {result.graph.truncated
            ? "Summary view"
            : result.graph.nodes.length < result.metrics.nodes
              ? "Filtered view"
              : "Full network"}
        </span>
      </div>
      <div className="graph-toolbar">
        <label className="search-field">
          <Search size={15} />
          <input
            aria-label="Search pseudonymous user ID"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Find a pseudonymous user…"
          />
        </label>
        <span className="graph-subtitle">
          UNDIRECTED · {result.config.weighted ? "WEIGHTED" : "UNWEIGHTED"}
        </span>
      </div>
      <div className="graph-canvas">
        <svg
          viewBox="0 0 860 550"
          role="img"
          aria-label={`Interaction network with ${result.graph.nodes.length} visible nodes`}
        >
          <defs>
            <pattern
              id="grid"
              width="25"
              height="25"
              patternUnits="userSpaceOnUse"
            >
              <circle cx="2" cy="2" r=".6" fill="#77939b" opacity=".28" />
            </pattern>
          </defs>
          <rect width="860" height="550" fill="url(#grid)" />
          <g
            transform={`translate(430 275) scale(${zoom}) translate(-430 -275)`}
          >
            {result.graph.edges.map((edge) => {
              const a = nodes.get(edge.source),
                b = nodes.get(edge.target);
              if (!a || !b) return null;
              const active =
                !selected ||
                (a.community_id === selected && b.community_id === selected);
              return (
                <line
                  key={`${edge.source}-${edge.target}`}
                  x1={430 + a.x * 275}
                  y1={275 + a.y * 245}
                  x2={430 + b.x * 275}
                  y2={275 + b.y * 245}
                  stroke={
                    a.community_id === b.community_id
                      ? communityColor(a.community_id)
                      : "#829197"
                  }
                  strokeWidth={0.6 + Math.min(edge.weight, 5) * 0.12}
                  opacity={active ? 0.18 : 0.025}
                />
              );
            })}
            {result.graph.nodes.map((node) => {
              const active =
                (!selected || node.community_id === selected) &&
                (!search || matches.includes(node.id));
              return (
                <g
                  key={node.id}
                  role="button"
                  tabIndex={0}
                  aria-label={`${node.id}, ${node.community_id}, ${node.degree} connections`}
                  className="graph-node"
                  opacity={active ? 1 : 0.12}
                  onClick={() => {
                    setNodeID(node.id);
                    onSelect(node.community_id);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setNodeID(node.id);
                      onSelect(node.community_id);
                    }
                  }}
                >
                  <title>
                    {node.id} · {node.community_id} · degree {node.degree}
                  </title>
                  <circle
                    cx={430 + node.x * 275}
                    cy={275 + node.y * 245}
                    r={6 + Math.min(node.degree, 18) * 0.3}
                    fill={communityColor(node.community_id)}
                    stroke="#10191e"
                    strokeWidth="2"
                  />
                  {node.id === nodeID && (
                    <circle
                      cx={430 + node.x * 275}
                      cy={275 + node.y * 245}
                      r="16"
                      fill="none"
                      stroke="#edf2e9"
                    />
                  )}
                </g>
              );
            })}
          </g>
          {!result.graph.nodes.length && (
            <text x="430" y="270" fill="#a5b2b4" textAnchor="middle">
              No nodes match this analysis configuration.
            </text>
          )}
        </svg>
        <div className="graph-controls">
          <button
            aria-label="Zoom out"
            onClick={() => setZoom(Math.max(0.6, zoom - 0.2))}
          >
            <Minus size={16} />
          </button>
          <button aria-label="Reset graph view" onClick={() => setZoom(1)}>
            <Maximize2 size={15} />
          </button>
          <button
            aria-label="Zoom in"
            onClick={() => setZoom(Math.min(3, zoom + 0.2))}
          >
            <Plus size={16} />
          </button>
        </div>
        <div className="graph-caption">
          <span className="status-dot" />
          {result.graph.nodes.length} shown / {result.metrics.nodes} total nodes{" "}
          <span>·</span> {result.graph.edges.length} visible edges
        </div>
      </div>
      <div className="graph-footer">
        {current ? (
          <>
            <strong>{current.id}</strong>
            <span>
              {current.community_id} · {current.degree} connections
            </span>
          </>
        ) : (
          <>
            <span>
              Every node is a pseudonymous user. Every edge is an observed
              interaction.
            </span>
            <span>Select a node to inspect ↗</span>
          </>
        )}
      </div>
      {search && (
        <div className="search-results" aria-live="polite">
          {matches.length
            ? `${matches.length} matching IDs in the full result. ${matches.filter((id) => nodes.has(id)).length} shown in this view.`
            : "No matching IDs. Search uses pseudonyms from this run."}
        </div>
      )}
    </section>
  );
}
