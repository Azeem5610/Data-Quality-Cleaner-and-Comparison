// Empty base URL uses the Vite dev proxy (/api -> backend on port 8000).
// Set VITE_API_BASE_URL (e.g. http://localhost:8000) to call the backend directly.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function getHealth(): Promise<{ status: string }> {
  const res = await fetch(`${BASE_URL}/api/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}
