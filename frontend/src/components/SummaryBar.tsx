import { formatCost, formatLatency } from "../format";
import type { ClassifyResult } from "../types";

export default function SummaryBar({ result }: { result: ClassifyResult }) {
  return (
    <dl className="summary" aria-label="Request summary">
      <div>
        <dt>Cost</dt>
        <dd>
          {formatCost(result.cost_usd)}
          {result.cost_estimated && (
            <span className="estimated" title="Jev did not report token usage, so this is an estimate">
              {" "}
              estimated
            </span>
          )}
        </dd>
      </div>
      <div>
        <dt>Latency</dt>
        <dd>{formatLatency(result.latency_ms)}</dd>
      </div>
      <div>
        <dt>Model</dt>
        <dd>{result.model}</dd>
      </div>
    </dl>
  );
}
