import { DailyAnalysis, Fixture } from "./types";

const apiUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${await response.text()}`);
  }
  return response.json() as Promise<T>;
}

export const getDailyAnalysis = (date: string) =>
  apiFetch<DailyAnalysis>(`/api/v1/daily-analysis?date=${encodeURIComponent(date)}`);

export const getFixture = (id: string) => apiFetch<Fixture>(`/api/v1/fixtures/${id}`);

