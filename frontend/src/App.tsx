import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  Check,
  ChevronRight,
  CircleHelp,
  Cpu,
  FileCheck2,
  FileInput,
  FlaskConical,
  GitBranch,
  Layers3,
  LoaderCircle,
  Network,
  Play,
  RotateCcw,
  Settings2,
  ShieldCheck,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { api, ApiError } from "./api";
import type {
  AnalysisResult,
  Config,
  DatasetView,
  GraphSummary,
} from "./types";
import { defaultConfig } from "./types";
import { MetricCard } from "./components/MetricCard";
import { communityColor, NetworkGraph } from "./components/NetworkGraph";
import { filterPreview } from "./graphFilters";

const pages = [
  {
    name: "Data import",
    icon: FileInput,
    caption: "Start with your evidence",
    title: "A network begins with a conversation.",
  },
  {
    name: "Configure",
    icon: Settings2,
    caption: "Make the assumptions explicit",
    title: "Define your analytical lens.",
  },
  {
    name: "Explore",
    icon: Network,
    caption: "Explore the connections",
    title: "Interaction communities",
  },
  {
    name: "Evaluation",
    icon: FlaskConical,
    caption: "Measure, then interpret",
    title: "How strong is the signal?",
  },
  {
    name: "Export",
    icon: ArrowDownToLine,
    caption: "Keep the research reproducible",
    title: "Take the evidence with you.",
  },
];
const required = [
  "source_user",
  "target_user",
  "interaction_type",
  "timestamp",
  "subreddit",
];
const messages = (error: unknown) =>
  error instanceof Error
    ? error.message
    : "The request could not complete. Try again.";

function Panel({
  title,
  label,
  children,
}: {
  title: string;
  label: string;
  children: ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">{label}</span>
          <h2>{title}</h2>
        </div>
      </div>
      {children}
    </section>
  );
}
function Distribution({ result }: { result: AnalysisResult }) {
  const max = Math.max(1, ...result.communities.map((group) => group.size));
  return (
    <Panel title="Community size distribution" label="PARTITION STRUCTURE">
      <div className="distribution">
        {result.communities.slice(0, 20).map((group) => (
          <div className="bar-row" key={group.community_id}>
            <span>{group.community_id}</span>
            <div className="bar-track">
              <div
                style={{
                  width: `${(group.size / max) * 100}%`,
                  background: communityColor(group.community_id),
                }}
              />
            </div>
            <strong>{group.size}</strong>
          </div>
        ))}
        {!result.communities.length && (
          <p className="muted">No communities in this filtered run.</p>
        )}
        {result.communities.length > 20 && (
          <p className="muted">
            First 20 communities shown. All sizes are included in the JSON
            export.
          </p>
        )}
        <div className="chart-axis">
          <span>0</span>
          <span>NUMBER OF MEMBERS</span>
          <span>{max}</span>
        </div>
      </div>
    </Panel>
  );
}

export default function App() {
  const [page, setPage] = useState(0);
  const [dataset, setDataset] = useState<DatasetView | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [datasetName, setDatasetName] = useState("");
  const [config, setConfig] = useState<Config>({ ...defaultConfig });
  const [seedText, setSeedText] = useState("42, 7, 21");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [history, setHistory] = useState<AnalysisResult[]>([]);
  const [preview, setPreview] = useState<GraphSummary | null>(null);
  const [activeRun, setActiveRun] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [availableHeaders, setAvailableHeaders] = useState<string[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [selected, setSelected] = useState("");
  const [minimumSize, setMinimumSize] = useState(1);
  const [context, setContext] = useState("");
  const uploadRef = useRef<HTMLInputElement>(null);
  const running = Boolean(activeRun);
  const currentPage = pages[page];

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" });
  }, [page]);

  useEffect(() => {
    if (!activeRun) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let failures = 0;
    const poll = async () => {
      try {
        const job = await api.poll(activeRun, controller.signal);
        if (controller.signal.aborted) return;
        failures = 0;
        if (job.result) {
          setResult(job.result);
          setHistory((previous) => [...previous, job.result!].slice(-20));
          setSelected("");
          setContext("");
          setMinimumSize(1);
          setPage(2);
          setActiveRun(null);
          setNotice(
            "Analysis complete. These results are saved for this session.",
          );
          return;
        }
        if (job.status === "failed" || job.status === "cancelled") {
          setError(
            job.status === "cancelled"
              ? "Analysis cancelled. Earlier results are still available."
              : String(
                  job.error?.message ??
                    "Analysis could not complete. Earlier results are still available.",
                ),
          );
          setActiveRun(null);
          return;
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        if (++failures >= 3) {
          setError(`Could not retrieve analysis status. ${messages(error)}`);
          setActiveRun(null);
          return;
        }
      }
      timer = setTimeout(poll, 600);
    };
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [activeRun]);

  const task = async (work: () => Promise<void>) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await work();
    } catch (error) {
      setError(messages(error));
    } finally {
      setBusy(false);
    }
  };
  const upload = async (
    candidate: File,
    suppliedMapping: Record<string, string> = {},
  ) => {
    setFile(candidate);
    try {
      const validated = await api.upload(candidate, suppliedMapping);
      if (dataset)
        await api.removeDataset(dataset.dataset_id).catch(() => undefined);
      setDataset(validated);
      setDatasetName(candidate.name);
      setPreview(null);
      setAvailableHeaders([]);
      setMapping({});
      setConfig({ ...defaultConfig });
      setSeedText("42, 7, 21");
      setPage(0);
      setNotice(
        "Validation complete. Review data quality, then configure your analysis.",
      );
    } catch (error) {
      if (
        error instanceof ApiError &&
        Array.isArray(error.details.available_columns)
      ) {
        setAvailableHeaders(error.details.available_columns.map(String));
      }
      throw error;
    }
  };
  const validatedConfig = (): Config => {
    const seeds = seedText.trim()
      ? seedText.split(",").map((seed) => {
          if (!/^\s*\d+\s*$/.test(seed))
            throw new Error(
              "Stability seeds must be comma-separated nonnegative integers.",
            );
          return Number(seed.trim());
        })
      : [];
    if (
      seeds.length > 5 ||
      new Set(seeds).size !== seeds.length ||
      seeds.some((seed) => seed > 2 ** 32 - 1)
    )
      throw new Error(
        "Use at most five distinct stability seeds between 0 and 2³²−1.",
      );
    if (
      !Number.isInteger(config.seed) ||
      config.seed < 0 ||
      config.seed > 2 ** 32 - 1
    )
      throw new Error(
        "The primary seed must be an integer between 0 and 2³²−1.",
      );
    if (!(config.minimum_weight > 0) || !Number.isFinite(config.minimum_weight))
      throw new Error("Minimum edge weight must be a positive finite number.");
    if (!config.interaction_types.length)
      throw new Error("Select at least one interaction type.");
    return { ...config, stability_seeds: seeds };
  };
  const updateConfig = (patch: Partial<Config>) => {
    setConfig((previous) => ({ ...previous, ...patch }));
    setPreview(null);
  };
  const start = () =>
    task(async () => {
      if (!dataset) throw new Error("Import and validate a dataset first.");
      const job = await api.start(dataset.dataset_id, validatedConfig());
      setActiveRun(job.run_id);
    });
  const groups =
    result?.communities.filter(
      (group) =>
        group.size >= minimumSize && (!context || context in group.subreddits),
    ) ?? [];
  const eligibleGroups = new Set(groups.map((group) => group.community_id));
  const visibleResult = result
    ? { ...result, graph: filterPreview(result.graph, eligibleGroups) }
    : null;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          href="#"
          className="brand"
          onClick={(event) => {
            event.preventDefault();
            setPage(0);
          }}
        >
          <span className="brand-symbol">
            <Network size={23} />
          </span>
          <span>
            community<span className="brand-sub">OBSERVATORY</span>
          </span>
        </a>
        <div className="sidebar-section-label">RESEARCH WORKSPACE</div>
        <nav aria-label="Analysis workflow">
          {pages.map((item, index) => (
            <button
              key={item.name}
              className={`nav-item ${page === index ? "active" : ""}`}
              disabled={(index === 1 && !dataset) || (index > 1 && !result)}
              onClick={() => {
                setPage(index);
                setError("");
              }}
            >
              <item.icon size={18} />
              <span>{item.name}</span>
              <span className="nav-number">0{index + 1}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <GitBranch size={20} />
          <strong>Structure, before interpretation.</strong>
          <p>
            Label propagation detects interaction patterns. Academic interests
            need separate evidence.
          </p>
        </div>
        <div className="sidebar-bottom">
          <span className="status-dot" /> LOCAL RESEARCH SESSION
          <span>v1.0 · NetworkX LPA</span>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            WORKSPACE <ChevronRight size={13} />
            <span>REDDIT NETWORKS</span>
          </div>
          <div className="session-label">
            <ShieldCheck size={15} />
            Pseudonymous by default
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <p className="eyebrow accent">{currentPage.caption}</p>
              <h1>{currentPage.title}</h1>
              <p className="page-description">
                {page === 0
                  ? "Turn an interaction dataset into transparent, reproducible research."
                  : page === 2
                    ? "Follow the connections. Inspect the partition. Keep the assumptions visible."
                    : "A clear record of the data, decisions, and results behind your analysis."}
              </p>
            </div>
            <div className="heading-actions">
              {running ? (
                <button
                  className="button secondary"
                  onClick={() =>
                    void task(async () => {
                      await api.cancel(activeRun!);
                      setActiveRun(null);
                      setNotice(
                        "Analysis cancelled. Earlier successful results are preserved.",
                      );
                    })
                  }
                >
                  <X size={16} />
                  Cancel analysis
                </button>
              ) : page > 0 && dataset ? (
                <button
                  className="button primary"
                  disabled={busy}
                  onClick={() => void start()}
                >
                  <Play size={15} />
                  {result ? "Run again" : "Run detection"}
                </button>
              ) : (
                <span className="pill">
                  <FlaskConical size={13} />
                  RESEARCH EDITION
                </span>
              )}
            </div>
          </div>
          {error && (
            <div className="banner error" role="alert">
              <CircleHelp size={18} />
              <span>{error}</span>
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          {notice && (
            <div className="banner notice" role="status">
              <Check size={17} />
              <span>{notice}</span>
              <button
                aria-label="Dismiss notification"
                onClick={() => setNotice("")}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {running && (
            <div className="banner running" role="status">
              <LoaderCircle className="spin" size={18} />
              <span>
                Validating the graph, propagating labels, and comparing seeds…{" "}
                <small>A worker enforces the 60-second deadline.</small>
              </span>
            </div>
          )}
          {result && page >= 2 && (
            <>
              <div className="result-meta">
                <span className="status-dot" /> SAVED RESULT{" "}
                <span className="mono">{result.run_id.slice(0, 8)}</span>
                <span>
                  SEED {result.config.seed} ·{" "}
                  {result.config.weighted ? "WEIGHTED" : "UNWEIGHTED"} ·{" "}
                  {new Date(result.provenance.created_at).toLocaleString()}
                </span>
                {history.length > 1 && (
                  <label>
                    Run{" "}
                    <select
                      aria-label="Select saved run"
                      value={result.run_id}
                      onChange={(event) => {
                        setResult(
                          history.find(
                            (item) => item.run_id === event.target.value,
                          )!,
                        );
                        setSelected("");
                      }}
                    >
                      {history.map((item) => (
                        <option key={item.run_id} value={item.run_id}>
                          {item.run_id.slice(0, 8)} · seed {item.config.seed}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </div>
              <div className="metrics-grid">
                <MetricCard
                  index={0}
                  label="Eligible users"
                  value={result.metrics.nodes}
                  detail="One pseudonymous node per user"
                />
                <MetricCard
                  index={1}
                  label="Interaction edges"
                  value={result.metrics.edges}
                  detail="Aggregated unique user pairs"
                />
                <MetricCard
                  index={2}
                  label="Detected communities"
                  value={result.metrics.communities}
                  detail="A complete, disjoint partition"
                />
                <MetricCard
                  index={3}
                  label="Weighted modularity"
                  value={result.metrics.modularity}
                  detail={
                    result.metrics.modularity === null
                      ? "Undefined for graphs without edges"
                      : "Structure score, not ground truth"
                  }
                />
              </div>
            </>
          )}

          {page === 0 && (
            <>
              <div className="import-grid">
                <section className="panel upload-panel">
                  <span className="step-tag">01 / DATA IMPORT</span>
                  <Upload size={33} strokeWidth={1.3} />
                  <h2>Bring your interaction data.</h2>
                  <p>
                    Upload a canonical edge-list CSV. We’ll validate the records
                    before any graph is built.
                  </p>
                  <input
                    ref={uploadRef}
                    type="file"
                    accept=".csv,text/csv"
                    aria-label="Upload interaction CSV"
                    className="file-input"
                    disabled={busy || running}
                    onChange={(event) => {
                      const candidate = event.target.files?.[0];
                      if (candidate) {
                        setAvailableHeaders([]);
                        setMapping({});
                        void task(() => upload(candidate));
                      }
                      event.target.value = "";
                    }}
                  />
                  <button
                    className="button primary"
                    disabled={busy || running}
                    onClick={() => uploadRef.current?.click()}
                  >
                    {busy ? (
                      <LoaderCircle className="spin" size={16} />
                    ) : (
                      <Upload size={16} />
                    )}
                    Choose CSV file
                  </button>
                  <span className="upload-limit">
                    UTF-8 · up to 5 MiB · 50,000 rows
                  </span>
                  <div className="upload-divider">
                    <span>or begin with a reproducible example</span>
                  </div>
                  <button
                    className="sample-button"
                    disabled={busy || running}
                    onClick={() =>
                      void task(async () => upload(await api.sample()))
                    }
                  >
                    <span className="sample-icon">
                      <FlaskConical size={21} />
                    </span>
                    <span>
                      <strong>Explore the synthetic sample</strong>
                      <small>
                        48 users · four connected academic discussion groups
                      </small>
                    </span>
                    <ArrowRight size={18} />
                  </button>
                  <a className="text-link" href="/api/v1/sample" download>
                    Download sample CSV <ArrowDownToLine size={13} />
                  </a>
                </section>
                <Panel title="A clear input contract" label="BEFORE YOU UPLOAD">
                  <div className="schema-table">
                    <div className="schema-table-head">
                      <span>REQUIRED FIELD</span>
                      <span>EXPECTED VALUE</span>
                    </div>
                    {[
                      ["source_user", "Interaction initiator"],
                      ["target_user", "Interaction recipient"],
                      [
                        "interaction_type",
                        "reply / mention / shared_discussion",
                      ],
                      ["timestamp", "ISO-8601 with timezone"],
                      ["subreddit", "Discussion context; may be empty"],
                    ].map(([key, value]) => (
                      <div key={key}>
                        <code>{key}</code>
                        <span>{value}</span>
                      </div>
                    ))}
                  </div>
                  <div className="contract-note">
                    <ShieldCheck size={19} />
                    <p>
                      IDs are pseudonymized in results. Invalid rows are
                      quarantined; duplicates and self-loops are counted
                      separately.
                    </p>
                  </div>
                  <p className="panel-footnote">
                    Optional fields: interaction_id, weight, post_id, text. Text
                    is never included in public artifacts.
                  </p>
                </Panel>
              </div>
              {availableHeaders.length > 0 && file && (
                <Panel title="Map your column names" label="SCHEMA RECOVERY">
                  <p className="panel-copy">
                    Select the source header for each required field, then
                    validate the same file again.
                  </p>
                  <div className="mapping-grid">
                    {required.map((field) => (
                      <label key={field}>
                        {field}
                        <select
                          aria-label={`Map ${field}`}
                          value={
                            Object.entries(mapping).find(
                              ([, target]) => target === field,
                            )?.[0] ??
                            (availableHeaders.includes(field) ? field : "")
                          }
                          onChange={(event) => {
                            const source = event.target.value;
                            setMapping((previous) => {
                              const next = { ...previous };
                              for (const key of Object.keys(next))
                                if (next[key] === field) delete next[key];
                              if (source && source !== field)
                                next[source] = field;
                              return next;
                            });
                          }}
                        >
                          <option value="">Choose source column</option>
                          {availableHeaders.map((header) => (
                            <option key={header}>{header}</option>
                          ))}
                        </select>
                      </label>
                    ))}
                  </div>
                  <button
                    className="button primary"
                    disabled={busy}
                    onClick={() => void task(() => upload(file, mapping))}
                  >
                    Validate mapped CSV <ArrowRight size={15} />
                  </button>
                </Panel>
              )}
              {dataset && (
                <Panel title="Data quality report" label="VALIDATED DATASET">
                  <div className="quality-header">
                    <span>
                      <FileCheck2 size={18} />
                      {datasetName}
                    </span>
                    <button
                      className="button subtle"
                      disabled={running || busy}
                      onClick={() =>
                        void task(async () => {
                          await api.removeDataset(dataset.dataset_id);
                          setDataset(null);
                          setFile(null);
                          setPreview(null);
                          setNotice("Uploaded dataset deleted.");
                        })
                      }
                    >
                      <Trash2 size={15} />
                      Delete upload
                    </button>
                  </div>
                  <div className="quality-grid">
                    {[
                      ["Input rows", dataset.quality.input_rows],
                      ["Accepted", dataset.quality.accepted_rows],
                      ["Quarantined", dataset.quality.rejected_rows],
                      ["Duplicates", dataset.quality.duplicate_rows],
                      ["Self-loops", dataset.quality.self_loops],
                    ].map(([label, count]) => (
                      <div key={label}>
                        <strong>{count}</strong>
                        <span>{label}</span>
                      </div>
                    ))}
                  </div>
                  {dataset.quality.rejections?.length ? (
                    <div className="rejections">
                      <h3>Quarantine reasons (first 50)</h3>
                      {dataset.quality.rejections.map((rejection) => (
                        <p key={rejection.row}>
                          <code>
                            Row {rejection.row} / {rejection.code}
                          </code>{" "}
                          {rejection.message}
                        </p>
                      ))}
                    </div>
                  ) : (
                    <p className="panel-copy success-text">
                      <Check size={15} />
                      All rows meet the input contract.
                    </p>
                  )}
                  <div className="quality-footer">
                    <span>
                      SHA-256 <code>{dataset.fingerprint.slice(0, 18)}…</code>
                    </span>
                    <button
                      className="button primary"
                      onClick={() => setPage(1)}
                    >
                      Configure analysis <ArrowRight size={15} />
                    </button>
                  </div>
                </Panel>
              )}
              <div className="method-strip">
                <span>
                  <Network size={19} />
                  Interaction graph
                </span>
                <ArrowRight size={16} />
                <span>
                  <Cpu size={19} />
                  Label propagation
                </span>
                <ArrowRight size={16} />
                <span>
                  <FlaskConical size={19} />
                  Evaluation
                </span>
                <ArrowRight size={16} />
                <span>
                  <ArrowDownToLine size={19} />
                  Reproducible evidence
                </span>
              </div>
            </>
          )}

          {page === 1 && dataset && (
            <div className="configuration-grid">
              <Panel
                title="Graph & algorithm settings"
                label="ANALYSIS CONFIGURATION"
              >
                <div className="form-grid">
                  <label>
                    Primary random seed
                    <input
                      aria-label="Primary random seed"
                      type="number"
                      min="0"
                      max={2 ** 32 - 1}
                      value={config.seed}
                      onChange={(event) =>
                        updateConfig({ seed: event.target.valueAsNumber })
                      }
                    />
                    <small>
                      Same data + settings + environment → same partition.
                    </small>
                  </label>
                  <label>
                    Minimum aggregated edge weight
                    <input
                      aria-label="Minimum edge weight"
                      type="number"
                      min="0.001"
                      step="any"
                      value={config.minimum_weight}
                      onChange={(event) =>
                        updateConfig({
                          minimum_weight: event.target.valueAsNumber,
                        })
                      }
                    />
                    <small>
                      Thresholding retains disconnected users as isolates.
                    </small>
                  </label>
                  <label>
                    Start time (UTC)
                    <input
                      aria-label="Start time UTC"
                      type="datetime-local"
                      value={config.start_time?.slice(0, 16) ?? ""}
                      onChange={(event) =>
                        updateConfig({
                          start_time: event.target.value
                            ? `${event.target.value}:00Z`
                            : null,
                        })
                      }
                    />
                  </label>
                  <label>
                    End time (UTC)
                    <input
                      aria-label="End time UTC"
                      type="datetime-local"
                      value={config.end_time?.slice(0, 16) ?? ""}
                      onChange={(event) =>
                        updateConfig({
                          end_time: event.target.value
                            ? `${event.target.value}:00Z`
                            : null,
                        })
                      }
                    />
                  </label>
                  <label>
                    Subreddit filter
                    <select
                      aria-label="Subreddit filter"
                      value={config.subreddits[0] ?? ""}
                      onChange={(event) =>
                        updateConfig({
                          subreddits: event.target.value
                            ? [event.target.value]
                            : [],
                        })
                      }
                    >
                      <option value="">All discussion contexts</option>
                      {dataset.subreddits.map((topic) => (
                        <option key={topic}>{topic}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Stability seeds
                    <input
                      aria-label="Stability seeds"
                      value={seedText}
                      onChange={(event) => {
                        setSeedText(event.target.value);
                        setPreview(null);
                      }}
                      placeholder="42, 7, 21"
                    />
                    <small>
                      Up to five seeds; leave empty to skip comparison.
                    </small>
                  </label>
                </div>
                <fieldset className="interaction-options">
                  <legend>Interaction types</legend>
                  {defaultConfig.interaction_types.map((kind) => (
                    <label key={kind}>
                      <input
                        type="checkbox"
                        checked={config.interaction_types.includes(kind)}
                        onChange={(event) =>
                          updateConfig({
                            interaction_types: event.target.checked
                              ? [...config.interaction_types, kind]
                              : config.interaction_types.filter(
                                  (item) => item !== kind,
                                ),
                          })
                        }
                      />
                      {kind.replace("_", " ")}
                    </label>
                  ))}
                </fieldset>
                <div className="toggle-options">
                  <label>
                    <input
                      type="checkbox"
                      checked={config.weighted}
                      onChange={(event) =>
                        updateConfig({ weighted: event.target.checked })
                      }
                    />
                    <span>
                      <strong>Use interaction weights</strong>
                      <small>
                        Sum distinct events before applying edge thresholds.
                      </small>
                    </span>
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={config.largest_component_only}
                      onChange={(event) =>
                        updateConfig({
                          largest_component_only: event.target.checked,
                        })
                      }
                    />
                    <span>
                      <strong>Keep only the largest connected component</strong>
                      <small>Removed nodes are reported explicitly.</small>
                    </span>
                  </label>
                </div>
                <div className="form-actions">
                  <button
                    className="button secondary"
                    disabled={busy || running}
                    onClick={() => {
                      setConfig({ ...defaultConfig });
                      setSeedText("42, 7, 21");
                      setPreview(null);
                    }}
                  >
                    <RotateCcw size={15} />
                    Reset
                  </button>
                  <button
                    className="button secondary"
                    disabled={busy || running}
                    onClick={() =>
                      void task(async () =>
                        setPreview(
                          await api.preview(
                            dataset.dataset_id,
                            validatedConfig(),
                          ),
                        ),
                      )
                    }
                  >
                    Preview graph
                  </button>
                  <button
                    className="button primary"
                    disabled={busy || running}
                    onClick={() => void start()}
                  >
                    <Play size={15} />
                    Run detection
                  </button>
                </div>
              </Panel>
              <div className="config-aside">
                <Panel
                  title="Your analytical frame"
                  label="TRANSPARENT BY DESIGN"
                >
                  <dl className="definition-list">
                    <dt>Algorithm</dt>
                    <dd>Asynchronous label propagation</dd>
                    <dt>Graph policy</dt>
                    <dd>Simple, undirected; eligible isolates retained</dd>
                    <dt>Environment</dt>
                    <dd>Pinned Python + NetworkX</dd>
                    <dt>Deadline</dt>
                    <dd>60 seconds per worker</dd>
                    <dt>Input window</dt>
                    <dd>
                      {new Date(dataset.start_time).toLocaleDateString()} —{" "}
                      {new Date(dataset.end_time).toLocaleDateString()}
                    </dd>
                  </dl>
                  <p className="panel-footnote">
                    LPA uses seeded random update order and tie-breaking.
                    Community IDs have no intrinsic topic meaning.
                  </p>
                </Panel>
                {preview && (
                  <Panel title="Graph preview" label="BEFORE EXECUTION">
                    <dl className="definition-list">
                      {Object.entries(preview).map(([key, value]) => (
                        <div className="definition-row" key={key}>
                          <dt>{key.replaceAll("_", " ")}</dt>
                          <dd>{value}</dd>
                        </div>
                      ))}
                    </dl>
                  </Panel>
                )}
              </div>
            </div>
          )}

          {page === 2 && result && visibleResult && (
            <>
              <div className="explorer-layout">
                <NetworkGraph
                  key={result.run_id}
                  result={visibleResult}
                  selected={selected}
                  onSelect={setSelected}
                />
                <section className="panel community-panel">
                  <div className="panel-heading">
                    <div>
                      <span className="eyebrow">THE PARTITION</span>
                      <h2>Community lens</h2>
                    </div>
                    <span className="count-badge">{groups.length}</span>
                  </div>
                  <div className="community-filters">
                    <label>
                      Minimum members
                      <input
                        aria-label="Minimum community size"
                        type="number"
                        min="1"
                        value={minimumSize}
                        onChange={(event) => {
                          setMinimumSize(
                            Math.max(1, event.target.valueAsNumber || 1),
                          );
                          setSelected("");
                        }}
                      />
                    </label>
                    <label>
                      Discussion context
                      <select
                        aria-label="Discussion context filter"
                        value={context}
                        onChange={(event) => {
                          setContext(event.target.value);
                          setSelected("");
                        }}
                      >
                        <option value="">All contexts</option>
                        {Array.from(
                          new Set(
                            result.communities.flatMap((group) =>
                              Object.keys(group.subreddits),
                            ),
                          ),
                        )
                          .sort()
                          .map((topic) => (
                            <option key={topic}>{topic}</option>
                          ))}
                      </select>
                    </label>
                  </div>
                  <button
                    className={`community-row ${!selected ? "selected" : ""}`}
                    onClick={() => setSelected("")}
                  >
                    <span className="community-marker all" />
                    <span>
                      <strong>All visible communities</strong>
                      <small>Reset highlighted partition</small>
                    </span>
                    <ArrowRight size={15} />
                  </button>
                  <div className="community-list">
                    {groups.slice(0, 100).map((group) => (
                      <button
                        className={`community-row ${selected === group.community_id ? "selected" : ""}`}
                        key={group.community_id}
                        onClick={() =>
                          setSelected(
                            selected === group.community_id
                              ? ""
                              : group.community_id,
                          )
                        }
                      >
                        <span
                          className="community-marker"
                          style={{
                            background: communityColor(group.community_id),
                          }}
                        />
                        <span>
                          <strong>
                            {group.community_id} <em>{group.size} members</em>
                          </strong>
                          <small>
                            {Object.keys(group.subreddits)[0]
                              ? `r/${Object.keys(group.subreddits)[0]}`
                              : "No discussion context"}
                          </small>
                        </span>
                        <ChevronRight size={15} />
                      </button>
                    ))}
                    {!groups.length && (
                      <p className="panel-copy muted">
                        No communities match these display filters.
                      </p>
                    )}
                    {groups.length > 100 && (
                      <p className="panel-copy muted">
                        First 100 of {groups.length} communities shown. Narrow
                        the filters or export all memberships.
                      </p>
                    )}
                  </div>
                  <div className="context-note">
                    <Layers3 size={17} />
                    <p>
                      Discussion context is a separate interpretation layer. It
                      does not define the graph partition.
                    </p>
                  </div>
                </section>
              </div>
              <div className="bottom-grid">
                <Distribution result={result} />
                <Panel title="A reproducible observation" label="RUN NOTEBOOK">
                  <dl className="definition-list compact">
                    <dt>Algorithm</dt>
                    <dd>NetworkX asynchronous LPA</dd>
                    <dt>Primary seed</dt>
                    <dd>{result.config.seed}</dd>
                    <dt>Analysis runtime</dt>
                    <dd>{result.metrics.runtime_seconds.toFixed(3)} s</dd>
                    <dt>Mean seed agreement</dt>
                    <dd>
                      {result.stability.mean_ari?.toFixed(3) ?? "Not requested"}
                    </dd>
                  </dl>
                  <button className="text-link" onClick={() => setPage(3)}>
                    Inspect evaluation <ArrowRight size={14} />
                  </button>
                </Panel>
              </div>
            </>
          )}

          {page === 3 && result && (
            <>
              <div className="bottom-grid">
                <Distribution result={result} />
                <Panel
                  title="Metrics, with their boundaries"
                  label="EVALUATION"
                >
                  <dl className="definition-list">
                    <dt>Internal edge fraction</dt>
                    <dd>
                      {result.metrics.intra_community_edge_fraction?.toFixed(
                        4,
                      ) ?? "Undefined without edges"}
                    </dd>
                    <dt>Minimum / median / maximum size</dt>
                    <dd>
                      {result.metrics.minimum_community_size} /{" "}
                      {result.metrics.median_community_size} /{" "}
                      {result.metrics.maximum_community_size}
                    </dd>
                    <dt>Isolated nodes</dt>
                    <dd>{result.summary.isolates}</dd>
                    <dt>Connected components</dt>
                    <dd>{result.summary.connected_components}</dd>
                    <dt>Actual analysis runtime</dt>
                    <dd>{result.metrics.runtime_seconds.toFixed(6)} seconds</dd>
                  </dl>
                  <p className="panel-footnote">
                    A high modularity value indicates graph structure. It does
                    not establish verified interests, expertise, or a correct
                    ground-truth partition.
                  </p>
                </Panel>
              </div>
              <Panel
                title="Sensitivity to initialization"
                label="MULTI-SEED STABILITY"
              >
                <p className="panel-copy">
                  Pairwise adjusted Rand index compares membership agreement
                  independent of community labels. 1 means identical partitions;
                  values near 0 indicate chance-level agreement.
                </p>
                <div className="stability-summary">
                  <strong>
                    {result.stability.mean_ari?.toFixed(4) ?? "—"}
                  </strong>
                  <span>MEAN PAIRWISE ARI</span>
                  <code>
                    Seeds:{" "}
                    {result.stability.seeds.join(", ") || "comparison skipped"}
                  </code>
                </div>
                {result.stability.comparisons.length > 0 && (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Seed A</th>
                        <th>Seed B</th>
                        <th>Adjusted Rand index</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.stability.comparisons.map((pair) => (
                        <tr key={`${pair.seed_a}-${pair.seed_b}`}>
                          <td>{pair.seed_a}</td>
                          <td>{pair.seed_b}</td>
                          <td>{pair.adjusted_rand_index.toFixed(6)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                <p className="panel-footnote">
                  Stable partitions are reproducible under seed changes;
                  stability alone does not validate their academic meaning.
                </p>
              </Panel>
              <Panel
                title="Data quality & run warnings"
                label="PIPELINE ACCOUNTING"
              >
                <div className="quality-grid">
                  {[
                    ["Input", result.quality.input_rows],
                    ["Accepted", result.quality.accepted_rows],
                    ["Rejected", result.quality.rejected_rows],
                    ["Duplicates", result.quality.duplicate_rows],
                    ["Self-loops", result.quality.self_loops],
                  ].map(([label, count]) => (
                    <div key={label}>
                      <strong>{count}</strong>
                      <span>{label}</span>
                    </div>
                  ))}
                </div>
                <p className="panel-copy">
                  Selected events: {result.summary.selected_events} · Filtered
                  events: {result.summary.filtered_events} · Threshold-removed
                  edges: {result.summary.threshold_removed_edges} ·
                  Component-removed nodes:{" "}
                  {result.summary.component_removed_nodes}
                </p>
                {result.warnings.map((warning) => (
                  <p className="warning-line" key={warning}>
                    <CircleHelp size={15} />
                    {warning}
                  </p>
                ))}
                {!result.warnings.length && (
                  <p className="panel-copy success-text">
                    <Check size={15} />
                    No run warnings.
                  </p>
                )}
              </Panel>
            </>
          )}

          {page === 4 && result && (
            <>
              <div className="export-grid">
                {[
                  {
                    format: "memberships.csv",
                    title: "Community memberships",
                    type: "CSV",
                    text: "One pseudonymous user per row, with community assignment and run ID.",
                  },
                  {
                    format: "result.json",
                    title: "Complete analytical artifact",
                    type: "JSON",
                    text: "Metrics, graph, memberships, settings, data quality, and software provenance.",
                  },
                  {
                    format: "report.md",
                    title: "Research summary",
                    type: "MARKDOWN",
                    text: "An actual-result report with limitations and a reproducibility record.",
                  },
                ].map((item) => (
                  <section className="panel export-card" key={item.format}>
                    <span className="file-type">{item.type}</span>
                    <ArrowDownToLine size={27} strokeWidth={1.4} />
                    <h2>{item.title}</h2>
                    <p>{item.text}</p>
                    <button
                      className="button secondary"
                      disabled={busy}
                      onClick={() =>
                        void task(() => api.download(result, item.format))
                      }
                    >
                      Download {item.type.toLowerCase()}{" "}
                      <ArrowDownToLine size={15} />
                    </button>
                  </section>
                ))}
              </div>
              <Panel title="The provenance record" label="TRACEABLE RESULTS">
                <dl className="provenance-list">
                  <dt>Run ID</dt>
                  <dd>{result.run_id}</dd>
                  <dt>Dataset SHA-256</dt>
                  <dd>{result.provenance.dataset_sha256}</dd>
                  <dt>Membership SHA-256</dt>
                  <dd>{result.provenance.membership_sha256}</dd>
                  <dt>Created (UTC)</dt>
                  <dd>{result.provenance.created_at}</dd>
                  <dt>Software</dt>
                  <dd>
                    Python {result.provenance.python_version} · NetworkX{" "}
                    {result.provenance.networkx_version} · Application{" "}
                    {result.provenance.application_version}
                  </dd>
                  <dt>Identifier policy</dt>
                  <dd>{result.provenance.identifier_policy}</dd>
                </dl>
                <details>
                  <summary>Saved analysis configuration</summary>
                  <pre>{JSON.stringify(result.config, null, 2)}</pre>
                </details>
                <div className="form-actions">
                  <button
                    className="button subtle"
                    disabled={busy || running}
                    onClick={() =>
                      void task(async () => {
                        await api.cancel(result.run_id);
                        const remaining = history.filter(
                          (item) => item.run_id !== result.run_id,
                        );
                        setHistory(remaining);
                        setResult(remaining.at(-1) ?? null);
                        if (!remaining.length) setPage(dataset ? 1 : 0);
                        setNotice("Saved run deleted from this session.");
                      })
                    }
                  >
                    <Trash2 size={15} />
                    Delete saved run
                  </button>
                </div>
                <p className="panel-footnote">
                  Uploads and results expire after 30 minutes and are lost on
                  server restart. Download the artifacts you need. Pseudonyms
                  reduce casual exposure; they are not guaranteed anonymization.
                </p>
              </Panel>
            </>
          )}
          <footer className="workspace-footer">
            <span>COMMUNITY OBSERVATORY</span>
            <span>
              Interaction patterns are evidence. Interpretation is a research
              task.
            </span>
            <span>WEIGHTED LPA / v1.0</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
