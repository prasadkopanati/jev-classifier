// Display order and labels for the backend's fixed metrics (backend/app/questions.py).
export const METRICS: { id: string; label: string }[] = [
  { id: "intent", label: "Intent" },
  { id: "department", label: "Department" },
  { id: "frustration", label: "Frustration" },
  { id: "is_urgent", label: "Urgent" },
  { id: "refund_requested", label: "Refund requested" },
  { id: "wants_human", label: "Wants a human" },
  { id: "churn_risk", label: "Churn risk" },
];

export function labelFor(id: string): string {
  return METRICS.find((m) => m.id === id)?.label ?? id;
}

export function orderedIds(answerIds: string[]): string[] {
  const known = METRICS.map((m) => m.id).filter((id) => answerIds.includes(id));
  const extra = answerIds.filter((id) => !known.includes(id));
  return [...known, ...extra];
}
