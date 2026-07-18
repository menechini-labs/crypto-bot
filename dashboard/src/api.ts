// Thin fetch wrapper: consistent JSON parsing, timeout, and typed errors.
// Keeps components clean (no repeated try/catch per fetch) and robust
// (never hangs forever, surfaces failures clearly).

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const TIMEOUT_MS = 10_000;

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(url, { ...init, signal: ctrl.signal });
    let data: unknown = null;
    try {
      data = await res.json();
    } catch {
      // body não é JSON (ex.: erro de gateway); ignora e trata status abaixo
    }
    if (!res.ok) {
      const msg =
        data && typeof data === "object" && "error" in data
          ? String((data as { error: unknown }).error)
          : `HTTP ${res.status}`;
      throw new ApiError(msg, res.status);
    }
    return data as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new ApiError("Tempo esgotado (servidor lento?)", 408);
    }
    throw new ApiError(e instanceof Error ? e.message : "Erro de rede", 0);
  } finally {
    clearTimeout(t);
  }
}

export function apiGet<T>(url: string): Promise<T> {
  return request<T>(url);
}

export function apiPost<T>(url: string, body?: unknown): Promise<T> {
  return request<T>(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

/** Parse percent input ("2" -> 0.02) safely; returns null on invalid. */
export function parsePct(v: string): number | null {
  const n = parseFloat(v);
  if (!Number.isFinite(n) || n < 0) return null;
  return n / 100;
}

/** Parse price input; returns null on invalid. */
export function parseNum(v: string): number | null {
  const n = parseFloat(v);
  return Number.isFinite(n) ? n : null;
}
