export function asNumber(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function money(value: string | number | null | undefined): string {
  const number = asNumber(value);
  if (number === null) return "Unknown";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(number);
}

export function compactMoney(value: string | number | null | undefined): string {
  const number = asNumber(value);
  if (number === null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: number >= 100_000 ? "compact" : "standard",
    maximumFractionDigits: 0,
  }).format(number);
}

export function dateLabel(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

export function scoreLabel(value: string | number | null | undefined): string {
  const number = asNumber(value);
  return number === null ? "—" : Math.round(number).toString();
}

export function titleCase(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
