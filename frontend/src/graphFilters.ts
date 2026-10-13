import type { AnalysisResult } from "./types";

export function filterPreview(
  graph: AnalysisResult["graph"],
  groups: Set<string>,
): AnalysisResult["graph"] {
  const nodes = graph.nodes.filter((node) => groups.has(node.community_id));
  const ids = new Set(nodes.map((node) => node.id));
  return {
    ...graph,
    nodes,
    edges: graph.edges.filter(
      (edge) => ids.has(edge.source) && ids.has(edge.target),
    ),
  };
}
