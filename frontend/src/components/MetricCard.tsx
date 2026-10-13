import { useReducedMotion } from "motion/react";
import CountUp from "./CountUp";

export function MetricCard({
  label,
  value,
  detail,
  index,
}: {
  label: string;
  value: number | null;
  detail: string;
  index: number;
}) {
  const reduced = useReducedMotion();
  const displayed =
    value === null
      ? "—"
      : Number.isInteger(value)
        ? value
        : Number(value.toFixed(3));
  return (
    <div className="metric-card" style={{ animationDelay: `${index * 70}ms` }}>
      <span className="metric-label">
        {label}
        <span className="metric-index">0{index + 1}</span>
      </span>
      <div className="metric-value" aria-label={`${label}: ${displayed}`}>
        {typeof displayed === "number" && !reduced ? (
          <CountUp
            key={displayed}
            to={displayed}
            duration={0.8}
            separator=","
          />
        ) : (
          displayed
        )}
      </div>
      <span className="metric-detail">{detail}</span>
    </div>
  );
}
