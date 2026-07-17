import type {
  Strategy,
  BacktestParams,
  BacktestReport,
  AnalysisResult,
} from "./types";

const API_BASE = "/api";

async function request<T>(path: string, qs?: URLSearchParams): Promise<T> {
  const url = qs ? `${API_BASE}${path}?${qs}` : `${API_BASE}${path}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status} - ${res.statusText}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: Record<string, unknown>): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export async function fetchStrategies(
  filters?: Record<string, string | number>,
): Promise<Strategy[]> {
  const qs = new URLSearchParams();
  if (filters) {
    for (const [k, v] of Object.entries(filters)) {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    }
  }
  return request<Strategy[]>("/strategies", qs);
}

export async function fetchStats(): Promise<{
  totalStrategies: number;
  averagePnL: number | null;
  averageSharpe: number | null;
}> {
  return request("/stats");
}

export async function runBacktest(
  params: BacktestParams,
): Promise<{ report: BacktestReport; analysis: AnalysisResult }> {
  const resp = await post<{
    status: string;
    report: BacktestReport;
    analysis: AnalysisResult;
  }>("/backtest", params as unknown as Record<string, unknown>);
  return { report: resp.report, analysis: resp.analysis };
}

export async function fetchBacktestReport(
  id: string,
): Promise<{ report: BacktestReport; analysis: AnalysisResult }> {
  const resp = await request<{
    status: string;
    report: BacktestReport;
    analysis: AnalysisResult;
  }>(`/backtest/${id}`);
  return { report: resp.report, analysis: resp.analysis };
}

export async function triggerBacktestReflection(
  id: string,
): Promise<Record<string, unknown>> {
  const resp = await post<{ status: string; reflection: Record<string, unknown> }>(
    `/backtest/${id}/reflection`,
    {},
  );
  return resp.reflection;
}

export async function fetchReflections(
  limit = 10,
): Promise<Record<string, unknown>[]> {
  return request<{ status: string; reflections: Record<string, unknown>[] }>(
    "/reflections",
    new URLSearchParams({ limit: String(limit) }),
  ).then((r) => r.reflections);
}

