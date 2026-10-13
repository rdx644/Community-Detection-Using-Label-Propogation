import { expect, it } from "vitest";
import { filterPreview } from "../graphFilters";

const graph = {
  nodes: [
    { id: "a", community_id: "C001", degree: 1, x: 0, y: 0 },
    { id: "b", community_id: "C002", degree: 1, x: 1, y: 1 },
  ],
  edges: [{ source: "a", target: "b", weight: 1 }],
  truncated: false,
};
it("counts only displayed edges after a community filter", () => {
  expect(filterPreview(graph, new Set()).edges).toHaveLength(0);
  expect(filterPreview(graph, new Set(["C001"])).nodes).toHaveLength(1);
  expect(filterPreview(graph, new Set(["C001"])).edges).toHaveLength(0);
  expect(filterPreview(graph, new Set(["C001", "C002"])).edges).toHaveLength(1);
  expect(graph.edges).toHaveLength(1);
});
