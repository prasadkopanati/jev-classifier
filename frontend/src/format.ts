export function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function humanize(value: string): string {
  const text = value.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function formatCost(usd: number): string {
  return `$${usd.toFixed(6)}`;
}

export function formatLatency(ms: number): string {
  return `${Math.round(ms).toLocaleString("en-US")} ms`;
}
