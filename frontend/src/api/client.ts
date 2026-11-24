import type { AskRequest, AskResponse, ProcessResponse, SampleSource } from "../types";

// Empty base URL uses the Vite dev proxy (/api -> backend on port 8000).
// Set VITE_API_BASE_URL (e.g. http://localhost:8000) to call the backend directly.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function getHealth(): Promise<{ status: string }> {
  const res = await fetch(`${BASE_URL}/api/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

export async function askQuestion(request: AskRequest): Promise<AskResponse> {
  const res = await fetch(`${BASE_URL}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw await readError(res, "Question failed");
  return res.json();
}

async function readError(response: Response, fallback: string): Promise<Error> {
  const payload: unknown = await response.json().catch(() => null);
  if (payload && typeof payload === "object" && "detail" in payload && typeof payload.detail === "string") {
    return new Error(payload.detail);
  }
  return new Error(`${fallback} (${response.status})`);
}

export async function processFile(file: File): Promise<ProcessResponse> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${BASE_URL}/api/process`, { method: "POST", body: form });
  if (!response.ok) throw await readError(response, "Could not analyze this file");
  return response.json();
}

export async function processUrl(url: string): Promise<ProcessResponse> {
  const form = new FormData();
  form.append("url", url);
  const response = await fetch(`${BASE_URL}/api/process`, { method: "POST", body: form });
  if (!response.ok) throw await readError(response, "Could not analyze this URL");
  return response.json();
}

export async function getSamples(): Promise<SampleSource[]> {
  const response = await fetch(`${BASE_URL}/api/samples`);
  if (!response.ok) throw await readError(response, "Could not load demo samples");
  return response.json();
}

export async function loadSample(name: string): Promise<ProcessResponse> {
  const response = await fetch(`${BASE_URL}/api/samples/${encodeURIComponent(name)}`, { method: "POST" });
  if (!response.ok) throw await readError(response, "Could not load this demo sample");
  return response.json();
}
