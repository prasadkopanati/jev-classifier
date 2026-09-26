import { useState } from "react";

import { ApiError, classify } from "./api";
import ResultCards from "./components/ResultCards";
import type { ClassifyResult } from "./types";

const SAMPLE_TEXT =
  "I have been billed twice for the subscription and I want to review the charge and reverse it asap";

export default function App() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ClassifyResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = text.trim().length > 0 && !loading;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      setResult(await classify(text));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>Jev Classifier</h1>
      <p className="subtitle">
        Paste a customer message. Jev classifies it on intent, department,
        frustration and more.
      </p>

      <form onSubmit={submit}>
        <label htmlFor="query">Customer message</label>
        <textarea
          id="query"
          rows={5}
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={5000}
          placeholder="e.g. I was charged twice and want a refund"
        />
        <div className="actions">
          <button type="submit" disabled={!canSubmit}>
            {loading ? "Classifying…" : "Classify"}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => setText(SAMPLE_TEXT)}
            disabled={loading}
          >
            Use sample text
          </button>
        </div>
      </form>

      {error && <p role="alert">{error}</p>}
      {result && <ResultCards answers={result.answers} />}
    </main>
  );
}
