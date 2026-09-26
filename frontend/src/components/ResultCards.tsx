import { orderedIds } from "../metrics";
import type { Answer } from "../types";
import MetricCard from "./MetricCard";

export default function ResultCards({ answers }: { answers: Record<string, Answer> }) {
  return (
    <div className="cards">
      {orderedIds(Object.keys(answers)).map((id) => (
        <MetricCard key={id} id={id} answer={answers[id]} />
      ))}
    </div>
  );
}
