import { useState } from "react";
import type { SignalScoreResponse } from "./types";

/* Gera uma serie sintetica de closes para teste rapido */
function genSeries(n: number, kind: "uptrend" | "downtrend" | "lateral"): number[] {
  const out: number[] = [];
  let p = 100;
  for (let i = 0; i < n; i++) {
    if (kind === "uptrend") p += 0.5 + Math.sin(i / 5) * 0.2;
    else if (kind === "downtrend") p -= 0.5 + Math.sin(i / 5) * 0.2;
    else p += Math.sin(i / 3) * 1.5;
    out.push(Number(p.toFixed(2)));
  }
  return out;
}

function Bar({ label, value }: { label: string; value: number }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  const tone = value >= 0.66 ? "#2ecc71" : value >= 0.4 ? "#f1c40f" : "#e74c3c";
  return (
    <div className="score-bar">
      <span className="score-bar__label">{label}</span>
      <div className="score-bar__track">
        <div className="score-bar__fill" style={{ width: `${pct}%`, background: tone }} />
      </div>
      <span className="score-bar__val">{value.toFixed(2)}</span>
    </div>
  );
}

export default function ScorePanel() {
  const [closes, setCloses] = useState<string>("");
  const [signal, setSignal] = useState<"buy" | "sell" | "hold">("buy");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SignalScoreResponse | null>(null);

  async function runLLM() {
    setLoading(true);
    setError(null);
    try {
      const parsed = closes
        .split(",")
        .map((s) => Number(s.trim()))
        .filter((n) => !Number.isNaN(n));
      if (parsed.length < 20) {
        setError("Informe ao menos 20 valores de closes separados por vírgula.");
        setLoading(false);
        return;
      }
      const res = await fetch("/api/llm-signal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ closes: parsed, has_position: false, signal }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const j = (await res.json()) as SignalScoreResponse & { llm_enabled: boolean };
      setResult(j);
      setSignal(j.signal as "buy" | "sell" | "hold");
    } catch (e) {
      setError(e instanceof Error ? e.message : "erro");
    } finally {
      setLoading(false);
    }
  }

  async function runScore() {
    setLoading(true);
    setError(null);
    try {
      const parsed = closes
        .split(",")
        .map((s) => Number(s.trim()))
        .filter((n) => !Number.isNaN(n));
      if (parsed.length < 20) {
        setError("Informe ao menos 20 valores de closes separados por vírgula.");
        setLoading(false);
        return;
      }
      const res = await fetch("/api/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ closes: parsed, signal, has_position: false }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setResult((await res.json()) as SignalScoreResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : "erro");
    } finally {
      setLoading(false);
    }
  }

  const comp = result?.score?.details?.components;

  return (
    <section className="panel">
      <h2>Scoring de Sinal (LLM / Estratégia)</h2>
      <p className="hint">
        Cole uma série de closes (CSV) ou gere uma sintética. O backend aplica{" "}
        <code>score_signal</code> + <code>should_execute</code> (confiança ≥ 0.40, risco ≥ 0.50).
      </p>

      <div className="score-controls">
        <div className="score-row">
          <label>Sinal:</label>
          <select value={signal} onChange={(e) => setSignal(e.target.value as "buy" | "sell" | "hold")}>
            <option value="buy">BUY</option>
            <option value="sell">SELL</option>
            <option value="hold">HOLD</option>
          </select>
          <button type="button" onClick={() => setCloses(genSeries(60, "uptrend").join(","))}>
            Gerar uptrend
          </button>
          <button type="button" onClick={() => setCloses(genSeries(60, "lateral").join(","))}>
            Gerar lateral
          </button>
          <button type="button" onClick={() => setCloses(genSeries(60, "downtrend").join(","))}>
            Gerar downtrend
          </button>
          <button type="button" onClick={runLLM} disabled={loading}>
            Usar LLM
          </button>
        </div>
        <textarea
          rows={3}
          placeholder="100,101,102,103,... (>= 20 valores)"
          value={closes}
          onChange={(e) => setCloses(e.target.value)}
        />
        <button type="button" className="primary" onClick={runScore} disabled={loading}>
          {loading ? "Calculando..." : "Calcular Score"}
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      {result && (
        <div className="score-result">
          {!result.llm_enabled && (
            <p className="hint">LLM desativado (sem ENABLE_LLM=1 / LLM_API_KEY): usando fallback hold.</p>
          )}
          <div className="score-metrics">
            <Stat label="Confiança" value={`${(result.score.confidence * 100).toFixed(0)}%`} />
            <Stat label="Risco" value={`${(result.score.risk_score * 100).toFixed(0)}%`} />
            <Stat label="Composite" value={result.score.composite.toFixed(2)} />
            <Stat label="Regime" value={result.score.details.regime} />
          </div>
          {comp && (
            <div className="score-bars">
              <Bar label="trend" value={comp.trend} />
              <Bar label="momentum" value={comp.momentum} />
              <Bar label="volatility" value={comp.volatility} />
              <Bar label="risk_reward" value={comp.risk_reward} />
              <Bar label="regime" value={comp.regime} />
            </div>
          )}
          <p className="score-explain">{result.explanation}</p>
        </div>
      )}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <span className="stat__label">{label}</span>
      <span className="stat__value">{value}</span>
    </div>
  );
}
