import type { FactCheckResult, Metrics } from "./types";

// const API_BASE = "http://localhost:8080";
const API_BASE = import.meta.env.VITE_API_URL ?? "";

export async function factCheckClaim(claim: string): Promise<FactCheckResult> {
  const response = await fetch(`${API_BASE}/api/fact-check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ claim }),
  });
  if (!response.ok) throw new Error(`API error: ${response.status}`);
  return response.json();
}

export async function getMetrics(): Promise<Metrics> {
  const response = await fetch(`${API_BASE}/api/metrics`);
  if (!response.ok) throw new Error(`API error: ${response.status}`);
  return response.json();
}

