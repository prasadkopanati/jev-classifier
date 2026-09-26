import { percent } from "../format";

export interface BarRow {
  key: string;
  label: string;
  value: number;
  highlight?: boolean;
}

export default function ProbabilityBars({ rows }: { rows: BarRow[] }) {
  return (
    <ul className="bars">
      {rows.map((row) => (
        <li key={row.key} className={row.highlight ? "highlight" : undefined}>
          <span className="bar-label">{row.label}</span>
          <span className="bar-track" aria-hidden="true">
            <span
              className="bar-fill"
              style={{ width: `${Math.max(0, Math.min(1, row.value)) * 100}%` }}
            />
          </span>
          <span className="bar-value">{percent(row.value)}</span>
        </li>
      ))}
    </ul>
  );
}
