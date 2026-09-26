import type { ApiErrorBody, ClassifyResult } from "./types";

export class ApiError extends Error {
  code: string;

  constructor({ code, message }: ApiErrorBody) {
    super(message);
    this.code = code;
  }
}

const UNREACHABLE: ApiErrorBody = {
  code: "unreachable",
  message: "Could not reach the backend. Is it running on port 8000?",
};

async function request(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(path, init);
  } catch {
    throw new ApiError(UNREACHABLE);
  }
}

async function toApiError(resp: Response): Promise<ApiError> {
  try {
    const data = await resp.json();
    if (data?.error?.message) return new ApiError(data.error);
  } catch {
    // fall through to the generic message
  }
  return new ApiError({
    code: "http_error",
    message: `The server returned an unexpected error (HTTP ${resp.status}).`,
  });
}

export async function health(): Promise<boolean> {
  try {
    const resp = await fetch("/api/health");
    return resp.ok;
  } catch {
    return false;
  }
}

export async function classify(text: string): Promise<ClassifyResult> {
  const resp = await request("/api/classify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!resp.ok) throw await toApiError(resp);
  return (await resp.json()) as ClassifyResult;
}
