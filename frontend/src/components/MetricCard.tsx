import { humanize, percent } from "../format";
import { labelFor } from "../metrics";
import type { Answer, ChoiceAnswer, NoulAnswer, ScoreAnswer } from "../types";
import ProbabilityBars from "./ProbabilityBars";

function ChoiceBody({ answer }: { answer: ChoiceAnswer }) {
  const rows = Object.entries(answer.probabilities)
    .sort(([, a], [, b]) => b - a)
    .map(([key, value]) => ({
      key,
      label: humanize(key),
      value,
      highlight: key === answer.choice,
    }));
  return (
    <>
      <p className="value">{humanize(answer.choice)}</p>
      <p className="meta">Confidence {percent(answer.confidence)}</p>
      <ProbabilityBars rows={rows} />
    </>
  );
}

function nearestLevel(score: number, levels: string[]): string {
  return levels.reduce((best, level) =>
    Math.abs(Number(level) - score) < Math.abs(Number(best) - score) ? level : best,
  );
}

function ScoreBody({ answer }: { answer: ScoreAnswer }) {
  const levels = Object.keys(answer.legend).sort((a, b) => Number(a) - Number(b));
  const nearest = levels.length > 0 ? nearestLevel(answer.score, levels) : null;
  const rows = levels.map((level) => ({
    key: level,
    label: `${level}: ${answer.legend[level]}`,
    value: answer.probabilities[level] ?? 0,
    highlight: level === nearest,
  }));
  return (
    <>
      <p className="value">
        {answer.score.toFixed(2)}
        {nearest !== null && (
          <span className="value-note"> ≈ {answer.legend[nearest]}</span>
        )}
      </p>
      <p className="meta">Confidence {percent(answer.confidence)}</p>
      <ProbabilityBars rows={rows} />
    </>
  );
}

function NoulBody({ answer }: { answer: NoulAnswer }) {
  const yes = answer.noul >= 0.5;
  return (
    <>
      <p className="value">{yes ? "Yes" : "No"}</p>
      <p className="meta">Probability true</p>
      <ProbabilityBars
        rows={[{ key: "true", label: "True", value: answer.noul, highlight: yes }]}
      />
    </>
  );
}

export default function MetricCard({ id, answer }: { id: string; answer: Answer }) {
  return (
    <section className="card" aria-label={labelFor(id)}>
      <h3>
        {labelFor(id)} <span className="type-tag">{answer.type}</span>
      </h3>
      {answer.type === "choice" && <ChoiceBody answer={answer} />}
      {answer.type === "score" && <ScoreBody answer={answer} />}
      {answer.type === "noul" && <NoulBody answer={answer} />}
    </section>
  );
}
