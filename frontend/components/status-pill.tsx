import { titleCase } from "@/lib/format";

export function StatusPill({ value, kind = "pipeline" }: { value: string; kind?: "pipeline" | "market" }) {
  const tone = value === "ACTIVE" || value === "NEW" ? "positive" : value === "PENDING" || value === "REVIEWING" || value === "CONTACT_BROKER" || value === "DUE_DILIGENCE" ? "attention" : value === "OFF_MARKET" || value === "REJECTED" || value === "SOLD" ? "muted" : "neutral";
  return <span className={`status-pill status-${tone} status-${kind}`}>{titleCase(value)}</span>;
}
