import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { api, ApiError } from "../api";

vi.mock("../api", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api")>();
  return {
    ...original,
    api: {
      sample: vi.fn(),
      upload: vi.fn(),
      removeDataset: vi.fn(),
      start: vi.fn(),
      preview: vi.fn(),
      poll: vi.fn(),
      cancel: vi.fn(),
      download: vi.fn(),
    },
  };
});
const dataset = {
  dataset_id: "dataset-1",
  fingerprint: "f".repeat(64),
  quality: {
    input_rows: 3,
    accepted_rows: 2,
    rejected_rows: 1,
    duplicate_rows: 0,
    self_loops: 0,
    rejections: [
      { row: 3, code: "INVALID_WEIGHT", message: "Weight must be positive" },
    ],
  },
  columns: [],
  subreddits: ["science"],
  interaction_types: ["reply"],
  start_time: "2026-01-01T00:00:00Z",
  end_time: "2026-01-02T00:00:00Z",
  retention_seconds: 1800,
};

beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
});
describe("research workflow", () => {
  it("starts without invented metrics and requires validated input", () => {
    render(<App />);
    expect(
      screen.getByText("A network begins with a conversation."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Configure\s?02/ }),
    ).toBeDisabled();
    expect(screen.queryByText("Weighted modularity")).not.toBeInTheDocument();
  });
  it("validates the sample, reports quarantine and allows configuration", async () => {
    vi.mocked(api.sample).mockResolvedValue(
      new File(["sample"], "synthetic.csv"),
    );
    vi.mocked(api.upload).mockResolvedValue(dataset);
    render(<App />);
    fireEvent.click(
      screen.getByRole("button", { name: /Explore the synthetic sample/ }),
    );
    await screen.findByText("Data quality report");
    expect(screen.getByText("Weight must be positive")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Configure analysis/ }));
    expect(screen.getByLabelText("Primary random seed")).toHaveValue(42);
    fireEvent.change(screen.getByLabelText("Stability seeds"), {
      target: { value: "1, 1" },
    });
    fireEvent.click(
      screen.getAllByRole("button", { name: "Run detection" })[0],
    );
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "distinct stability seeds",
      ),
    );
    expect(api.start).not.toHaveBeenCalled();
  });
  it("offers column mapping on recoverable schema errors", async () => {
    vi.mocked(api.upload).mockRejectedValue(
      new ApiError("Required columns are missing", "MISSING_COLUMNS", {
        available_columns: ["author", "recipient", "kind", "date", "forum"],
      }),
    );
    render(<App />);
    fireEvent.change(screen.getByLabelText("Upload interaction CSV"), {
      target: { files: [new File(["a"], "mapped.csv")] },
    });
    await screen.findByText("Map your column names");
    expect(screen.getByLabelText("Map source_user")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Required columns are missing",
    );
  });
});
