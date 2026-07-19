import { useCallback, useEffect, useRef, useState } from "react";
import { apiPost } from "./api";

/* ------------------------------------------------------------------ */
/*  Tipos                                                             */
/* ------------------------------------------------------------------ */

interface PipelineCycle {
  cycle_id: number;
  timestamp: string;
  status: string;
  mode: string;
  agents?: Array<{
    name: string;
    role: string;
    verdict: string;
    confidence: number;
    reasoning: string;
    metrics?: Record<string, unknown>;
  }>;
  decision?: {
    name: string;
    verdict: string;
    confidence: number;
    reasoning: string;
    metrics?: Record<string, unknown>;
  };
  guard?: {
    passed: boolean;
    adjustments: string[];
    original_verdict: string;
    original_confidence: number;
    adjusted_verdict: string;
    adjusted_confidence: number;
  };
  blended_score?: {
    final_score: number;
    regime: string;
    contributions?: Array<{ source: string; value: number }>;
  };
  backtest?: {
    id: string;
    pnl_pct: number;
    win_rate: number;
    sharpe: number | null;
    total_trades: number;
    equity_curve: number[];
  };
  events?: Array<{
    type: string;
    content: string;
    timestamp: string;
  }>;
}

type StageId = "events" | "agents" | "score" | "guard" | "trade" | "backtest";

interface Stage {
  id: StageId;
  label: string;
  icon: string;
}

const STAGES: Stage[] = [
  { id: "events", label: "Eventos", icon: "⚡" },
  { id: "agents", label: "Agentes", icon: "⚇" },
  { id: "score", label: "Score", icon: "✦" },
  { id: "guard", label: "Guard", icon: "🛡" },
  { id: "trade", label: "Trade", icon: "⤬" },
  { id: "backtest", label: "Backtest", icon: "↻" },
];

function stageStatus(cycle: PipelineCycle | null, stage: StageId): "pending" | "running" | "ok" | "skipped" | "blocked" {
  if (!cycle) return "pending";
  switch (stage) {
    case "events":
      return cycle.events && cycle.events.length > 0 ? "ok" : "ok"; // always ok
    case "agents":
      return cycle.agents && cycle.agents.length > 0 ? "ok" : "skipped";
    case "score":
      return cycle.blended_score ? "ok" : "skipped";
    case "guard":
      return cycle.guard ? "ok" : "skipped";
    case "trade":
      return cycle.decision && cycle.decision.verdict !== "hold" ? "ok" : "skipped";
    case "backtest":
      return cycle.backtest ? "ok" : "skipped";
  }
}

function stageInfo(cycle: PipelineCycle | null, stage: StageId): string {
  if (!cycle) return "—";
  switch (stage) {
    case "events":
      return `${cycle.events?.length ?? 0} eventos`;
    case "agents":
      return `${cycle.agents?.length ?? 0} agentes`;
    case "score":
      return cycle.blended_score ? `${(cycle.blended_score.final_score * 100).toFixed(1)}%` : "n/a";
    case "guard":
      return cycle.guard ? (cycle.guard.passed ? "passou" : `${cycle.guard.adjustments.length} ajustes`) : "n/a";
    case "trade":
      return cycle.decision ? `${cycle.decision.verdict.toUpperCase()} @ ${(cycle.decision.confidence * 100).toFixed(0)}%` : "n/a";
    case "backtest":
      return cycle.backtest ? `${cycle.backtest.pnl_pct.toFixed(2)}%` : "n/a";
  }
}

/* ------------------------------------------------------------------ */
/*  Componente                                                        */
/* ------------------------------------------------------------------ */

export default function PipelineView() {
  const [cycle, setCycle] = useState<PipelineCycle | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const runCycle = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiPost<PipelineCycle>("/pipeline/cycle", {});
      setCycle(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "falha ao executar pipeline");
    } finally {
      setLoading(false);
    }
  }, []);

  // auto-refresh
  useEffect(() => {
    if (!autoRefresh) {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    runCycle();
    pollRef.current = setInterval(runCycle, 30000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [autoRefresh, runCycle]);

  const status = (s: Stage) => stageStatus(cycle, s.id);
  const info = (s: Stage) => stageInfo(cycle, s.id);

  return (
    <div className="pipeline">
      <div className="pipeline__header">
        <h2>Pipeline de Decisão</h2>
        <div className="pipeline__controls">
          <label className="toggle">
            <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
            <span>Auto 30s</span>
          </label>
          <button className="btn" onClick={runCycle} disabled={loading}>
            {loading ? "rodando..." : "Rodar ciclo"}
          </button>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}

      {/* Flow pipeline */}
      <div className="pipeline__flow">
        {STAGES.map((s, i) => (
          <div key={s.id} className={`pipeline__stage pipeline__stage--${status(s)}`}>
            <div className="pipeline__stage-icon">{s.icon}</div>
            <div className="pipeline__stage-label">{s.label}</div>
            <div className="pipeline__stage-info">{info(s)}</div>
            {i < STAGES.length - 1 && <div className="pipeline__arrow">→</div>}
          </div>
        ))}
      </div>

      {cycle && cycle.timestamp && (
        <p className="pipeline__ts">Último ciclo: {new Date(cycle.timestamp).toLocaleTimeString("pt-BR")} · id #{cycle.cycle_id}</p>
      )}

      {/* Agent details */}
      {cycle?.agents && cycle.agents.length > 0 && (
        <section className="panel pipeline__section">
          <h3>⚇ Agentes</h3>
          <div className="pipeline__agents">
            {cycle.agents.map((a) => (
              <div key={a.name} className={`agent-card agent-card--${a.verdict}`}>
                <div className="agent-card__header">
                  <strong>{a.name}</strong>
                  <span className={`badge badge--${a.verdict}`}>{a.verdict}</span>
                </div>
                <div className="agent-card__conf">conf: {(a.confidence * 100).toFixed(0)}%</div>
                <div className="agent-card__reason">{a.reasoning}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Guard detail */}
      {cycle?.guard && (
        <section className="panel pipeline__section">
          <h3>🛡 Guard</h3>
          <div className={`guard-result guard-result--${cycle.guard.passed ? "pass" : "fail"}`}>
            <div>
              <strong>Veredito original:</strong> {cycle.guard.original_verdict.toUpperCase()} @ {(cycle.guard.original_confidence * 100).toFixed(0)}%
            </div>
            <div>
              <strong>Ajustado:</strong> {cycle.guard.adjusted_verdict.toUpperCase()} @ {(cycle.guard.adjusted_confidence * 100).toFixed(0)}%
            </div>
            {cycle.guard.adjustments.length > 0 && (
              <ul className="guard-result__adj">
                {cycle.guard.adjustments.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            )}
            <div className={`badge badge--${cycle.guard.passed ? "ok" : "warn"}`}>
              {cycle.guard.passed ? "passou" : "bloqueado"}
            </div>
          </div>
        </section>
      )}

      {/* Blended Score */}
      {cycle?.blended_score && (
        <section className="panel pipeline__section">
          <h3>✦ Score Blended</h3>
          <div className="sig__blended-result">
            <div className="sig__blended-bar">
              <div className="sig__blended-fill" style={{ width: `${cycle.blended_score.final_score * 100}%` }} />
            </div>
            <div className="sig__blended-pct">{(cycle.blended_score.final_score * 100).toFixed(1)}%</div>
            <div className="sig__blended-regime">Regime: {cycle.blended_score.regime}</div>
          </div>
          {cycle.blended_score.contributions && (
            <table className="pipeline__table">
              <thead><tr><th>Fonte</th><th>Valor</th></tr></thead>
              <tbody>
                {cycle.blended_score.contributions.map((c, i) => (
                  <tr key={i}><td>{c.source}</td><td>{(c.value * 100).toFixed(1)}%</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}

      {/* Backtest result */}
      {cycle?.backtest && (
        <section className="panel pipeline__section">
          <h3>↻ Backtest</h3>
          <div className="pipeline__bt-grid">
            <div className="bt-stat"><span>PnL</span><strong className={cycle.backtest.pnl_pct >= 0 ? "pos" : "neg"}>{cycle.backtest.pnl_pct.toFixed(2)}%</strong></div>
            <div className="bt-stat"><span>Win Rate</span><strong>{(cycle.backtest.win_rate * 100).toFixed(1)}%</strong></div>
            {cycle.backtest.sharpe !== null && <div className="bt-stat"><span>Sharpe</span><strong>{cycle.backtest.sharpe.toFixed(2)}</strong></div>}
            <div className="bt-stat"><span>Trades</span><strong>{cycle.backtest.total_trades}</strong></div>
          </div>
          {cycle.backtest.equity_curve.length > 1 && (
            <div className="pipeline__sparkline">
              <Sparkline data={cycle.backtest.equity_curve} />
            </div>
          )}
        </section>
      )}

      {/* Events feed */}
      {cycle?.events && cycle.events.length > 0 && (
        <section className="panel pipeline__section">
          <h3>⚡ Eventos do ciclo</h3>
          <div className="evt-console">
            {cycle.events.slice(-10).reverse().map((ev, i) => (
              <div key={i} className="evt-console__entry">
                <span className="evt-console__type">{ev.type}</span>
                <span className="evt-console__msg">{ev.content}</span>
                <span className="evt-console__ts">{new Date(ev.timestamp).toLocaleTimeString("pt-BR")}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {!cycle && !loading && (
        <div className="empty">Clique em "Rodar ciclo" para iniciar o pipeline.</div>
      )}
    </div>
  );
}

/* Tiny sparkline SVG */
function Sparkline({ data }: { data: number[] }) {
  if (data.length < 2) return null;
  const w = 200;
  const h = 40;
  const mn = Math.min(...data);
  const mx = Math.max(...data);
  const rng = mx - mn || 1;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - mn) / rng) * h * 0.8 - h * 0.1}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} className="sparkline">
      <polyline fill="none" stroke="var(--accent)" strokeWidth="1.5" points={pts} />
    </svg>
  );
}
