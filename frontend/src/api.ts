import type {
  AnalysisResult,
  Config,
  DatasetView,
  GraphSummary,
  RunView,
} from "./types";

const base = "/api/v1";
export class ApiError extends Error {
  code: string;
  details: Record<string, unknown>;
  constructor(
    message: string,
    code: string,
    details: Record<string, unknown> = {},
  ) {
    super(message);
    this.code = code;
    this.details = details;
  }
}
function sessionID() {
  let id = sessionStorage.getItem("observatory-session");
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem("observatory-session", id);
  }
  return id;
}
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("X-Session-ID", sessionID());
  const response = await fetch(base + path, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(
      body?.error?.message ?? "The request could not complete. Try again.",
      body?.error?.code ?? "REQUEST_FAILED",
      body?.error?.details ?? {},
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});
export const api = {
  async sample() {
    const response = await fetch(base + "/sample");
    if (!response.ok) throw new Error("Sample dataset is unavailable.");
    return new File(
      [await response.blob()],
      "synthetic_sample_interactions.csv",
      { type: "text/csv" },
    );
  },
  upload(file: File, mapping: Record<string, string> = {}) {
    const form = new FormData();
    form.append("file", file);
    if (Object.keys(mapping).length)
      form.append("mapping", JSON.stringify(mapping));
    return request<DatasetView>("/datasets", { method: "POST", body: form });
  },
  preview: (id: string, config: Config) =>
    request<GraphSummary>(`/datasets/${id}/preview`, json(config)),
  start: (id: string, config: Config) =>
    request<RunView>("/runs", json({ dataset_id: id, config })),
  poll: (id: string, signal: AbortSignal) =>
    request<RunView>(`/runs/${id}`, { signal }),
  cancel: (id: string) => request<void>(`/runs/${id}`, { method: "DELETE" }),
  removeDataset: (id: string) =>
    request<void>(`/datasets/${id}`, { method: "DELETE" }),
  async download(result: AnalysisResult, format: string) {
    const response = await fetch(
      `${base}/runs/${result.run_id}/exports/${format}`,
      { headers: { "X-Session-ID": sessionID() } },
    );
    if (!response.ok)
      throw new ApiError(
        "Export is unavailable. The session may have expired.",
        "EXPORT_FAILED",
      );
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = `${result.run_id}-${format}`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
};
