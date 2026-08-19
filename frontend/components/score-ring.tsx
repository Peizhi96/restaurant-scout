import { scoreLabel } from "@/lib/format";

export function ScoreRing({
  value,
  label,
  size = "normal",
}: {
  value: string | number | null | undefined;
  label?: string;
  size?: "small" | "normal" | "large";
}) {
  const numeric = value === null || value === undefined ? 0 : Number(value);
  const known = Number.isFinite(numeric) && value !== null && value !== undefined;
  return (
    <div
      className={`score-ring score-ring-${size}`}
      style={{ "--score": `${known ? numeric : 0}%` } as React.CSSProperties}
      aria-label={`${label ?? "Score"}: ${known ? Math.round(numeric) : "unknown"}`}
    >
      <div>
        <strong>{scoreLabel(value)}</strong>
        {label ? <span>{label}</span> : null}
      </div>
    </div>
  );
}
