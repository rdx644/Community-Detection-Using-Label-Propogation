import type { components } from "./generated/api";

export type AnalysisResult = components["schemas"]["AnalysisResult"];
export type DatasetView = components["schemas"]["DatasetView"];
export type GraphSummary = components["schemas"]["GraphSummary"];
export type RunView = components["schemas"]["RunView"];
export type Config = Required<components["schemas"]["AnalysisConfig"]>;
export const defaultConfig: Config = {
  seed: 42,
  weighted: true,
  minimum_weight: 1,
  start_time: null,
  end_time: null,
  interaction_types: ["reply", "mention", "shared_discussion"],
  subreddits: [],
  largest_component_only: false,
  stability_seeds: [42, 7, 21],
};
