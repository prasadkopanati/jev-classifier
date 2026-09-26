// Mirrors the backend API contract (backend/app/schemas.py).

export interface ChoiceAnswer {
  type: "choice";
  choice: string;
  confidence: number;
  probabilities: Record<string, number>;
}

export interface ScoreAnswer {
  type: "score";
  score: number;
  confidence: number;
  legend: Record<string, string>;
  probabilities: Record<string, number>;
}

export interface NoulAnswer {
  type: "noul";
  noul: number;
}

export type Answer = ChoiceAnswer | ScoreAnswer | NoulAnswer;

export interface ClassifyResult {
  model: string;
  answers: Record<string, Answer>;
  cost_usd: number;
  cost_estimated: boolean;
  latency_ms: number;
  raw_response: unknown;
}

export interface ApiErrorBody {
  code: string;
  message: string;
}
