import { useEffect, useState } from "react";
import { apiGet, apiPost, parsePct, parseNum, ApiError } from "./api";
import type { Reflection } from "./types";

interface AgentRecord {
  name: string;
  role: string;
  verdict: string;
  confidence: number;
  reasoning: string;
  metrics: Record<string, unknown>;
}

interface Cycle {
  status: string;
  cycle_id: number;
  timestamp: string;
  paper_only: boolean;
  team?: string;
  agents: AgentRecord[];
  decision: AgentRecord | null;
  execution?: { executed: boolean; reason?: string };
}

interface LoopConfig {
  sl_pct?: number;
  tp_pct?: number;
  trailing_pct?: number;
  target_price?: number | null;
  auto_trade?: boolean;
  lock_stop?: boolean;
}

interface SwarmPreset {
  name: string;
  label?: string;
  team?: string;
}

const ROLE_LABEL: Record<string, string> = {
  market: "Mercado",
  news: "Notícias",
  risk: "Risco",
  strategy: "Estratégia",
  fusion: "Decision Core",
};

function AgentCard({ a }: { a: AgentRecord }) {
  const tone =
    a.verdict === "ok" || a.verdict === "buy"
      ? "ok"
      : a.verdict === "warn" || a.verdict === "sell"
      ? "warn"
      : a.verdict === "alert"
      ? "rej"
      : "neutral";
  return (
    <div className={`agent-card agent-card--${tone}`}>
      <div className="agent-card__head">
        <span className="agent-card__name">{a.name}</span>
        <span className="agent-card__role">{ROLE_LABEL[a.role] ?? a.role}</span>
        <span className={`agent-card__verdict agent-card__verdict--${tone}`}>{a.verdict.toUpperCase()}</span>
      </div>
      <p className="agent-card__reason">{a.reasoning}</p>
      <div className="agent-card__meta">
        <span>conf {a.confidence.toFixed(2)}</span>
        {Object.entries(a.metrics).slice(0, 4).map(([k, v]) => (
          <span key={k}>{k}: {typeof v === "object" ? JSON.stringify(v) : String(v)}</span>
        ))}
      </div>
    </div>
  );
}

interface SwarmPreset {
  name: string;
  description: string;
  strategy_focus: string;
  agents: string[];
}

const SWARM_DESC: Record<string, string> = {
  crypto_trading_desk: "Time cripto completo",
  investment_committee: "Comitê de investimento (lateral/baixa vol)",
  quant_desk: "Desk quant (tendência, sem news/risk)",
  risk_committee: "Comitê de risco (baixa, reduz exposição)",
  scalping_desk: "Scalping 1h (notícias em tempo real)",
  hedge_desk: "Hedge/monitoramento (só análise)",
};

export default function AgentDesk() {
  const [cycle, setCycle] = useState<Cycle | null>(null);
  const [presets, setPresets] = useState<SwarmPreset[]>([]);
  const [preset, setPreset] = useState<string>("crypto_trading_desk");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<string>("demo");
  const [executing, setExecuting] = useState(false);
  const [execMsg, setExecMsg] = useState<string | null>(null);
  const [loopRunning, setLoopRunning] = useState(false);
  const [loopBusy, setLoopBusy] = useState(false);
  const [cfg, setCfg] = useState({
    sl_pct: "2",
    tp_pct: "5",
    trailing_pct: "1",
    target_price: "",
    auto_trade: true,
    lock_stop: false,
  });
  const [reflOpen, setReflOpen] = useState(false);
  const [reflections, setReflections] = useState<Reflection[]>([]);
  const [reflBusy, setReflBusy] = useState(false);

  function handleApiErr(e: unknown, fallback: string) {
    setExecMsg(e instanceof ApiError ? `✗ ${e.message}` : e instanceof Error ? e.message : fallback);
  }

  async function loadLoopStatus() {
    try {
      const s = await apiGet<{ running: boolean; config?: LoopConfig }>("/api/agents/loop/status");
      setLoopRunning(Boolean(s.running));
      if (s.config) {
        setCfg((c) => ({
          ...c,
          sl_pct: s.config!.sl_pct != null ? String(s.config!.sl_pct * 100) : c.sl_pct,
          tp_pct: s.config!.tp_pct != null ? String(s.config!.tp_pct * 100) : c.tp_pct,
          trailing_pct: s.config!.trailing_pct != null ? String(s.config!.trailing_pct * 100) : c.trailing_pct,
          target_price: s.config!.target_price ? String(s.config!.target_price) : c.target_price,
          auto_trade: s.config!.auto_trade !== false,
          lock_stop: Boolean(s.config!.lock_stop),
        }));
      }
    } catch {
      /* silencioso */
    }
  }

  async function toggleLoop() {
    setLoopBusy(true);
    try {
      const url = loopRunning ? "/api/agents/loop/stop" : "/api/agents/loop/start";
      const sl = parsePct(cfg.sl_pct);
      const tp = parsePct(cfg.tp_pct);
      const tr = parsePct(cfg.trailing_pct);
      const target = cfg.target_price ? parseNum(cfg.target_price) : null;
      if (!loopRunning && (sl === null || tp === null || tr === null || (cfg.target_price !== "" && target === null))) {
        setExecMsg("✗ Valores inválidos (use números ≥ 0)");
        return;
      }
      const body = loopRunning
        ? {}
        : {
            team: preset,
            symbol: "BTCUSDT",
            interval: 20,
            sl_pct: sl ?? 0,
            tp_pct: tp ?? 0,
            trailing_pct: tr ?? 0,
            target_price: target,
            auto_trade: cfg.auto_trade,
            lock_stop: cfg.lock_stop,
          };
      const data = await apiPost<{ running: boolean; error?: string }>(url, body);
      setLoopRunning(Boolean(data.running));
      setExecMsg(data.running ? "▶ Loop ativo — agents decidem quando operar" : "■ Loop parado");
    } catch (e) {
      handleApiErr(e, "erro ao controlar loop");
    } finally {
      setLoopBusy(false);
    }
  }

  async function loadReflections() {
    try {
      const s = await apiGet<{ reflections: Reflection[] }>("/api/agents/reflections");
      setReflections(s.reflections ?? []);
    } catch {
      /* silencioso */
    }
  }

  async function reflectCycle() {
    if (!cycle) return;
    setReflBusy(true);
    try {
      await apiPost(`/api/agents/cycle/${cycle.cycle_id}/reflection`, {});
      setReflOpen(true);
      await loadReflections();
    } catch (e) {
      handleApiErr(e, "erro ao refletir");
    } finally {
      setReflBusy(false);
    }
  }

  async function loadPresets() {
    try {
      const data = await apiGet<SwarmPreset[]>("/api/swarm-presets");
      setPresets(data);
    } catch {
      /* silencioso */
    }
  }

  async function loadMode() {
    try {
      const m = await apiGet<{ mode: string }>("/api/mode");
      setMode(m.mode === "real" ? "real" : "demo");
    } catch {
      /* silencioso */
    }
  }

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<Cycle>(`/api/agents/cycle?team=${encodeURIComponent(preset)}`);
      setCycle(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : "erro ao carregar agentes");
    } finally {
      setLoading(false);
    }
  }

  async function execute() {
    if (!cycle) return;
    setExecuting(true);
    setExecMsg(null);
    try {
      const data = await apiPost<{ ok: boolean; error?: string; execution?: { result?: { order?: { side?: string; qty?: number | string } } } }>(
        "/api/agents/execute",
        { cycle_id: cycle.cycle_id, team: cycle.team ?? null },
      );
      if (data.ok) {
        const r = data.execution?.result ?? {};
        setExecMsg(`✓ Ordem ${r.order?.side?.toUpperCase()} ${r.order?.qty} executada`);
        load(); // refresh cycle
      } else {
        setExecMsg(`✗ ${data.error ?? "falha"}`);
      }
    } catch (e) {
      handleApiErr(e, "erro ao executar");
    } finally {
      setExecuting(false);
    }
  }

  useEffect(() => {
    loadPresets();
    loadMode();
    load();
    loadLoopStatus();
    loadReflections();
    const id = setInterval(load, 30_000);
    const id2 = setInterval(loadLoopStatus, 10_000);
    return () => { clearInterval(id); clearInterval(id2); };
  }, []);

  if (error) return <div className="error" role="alert">{error}</div>;
  if (!cycle) return <div className="loading">Carregando Agent Desk…</div>;

  const dec = cycle.decision;
  const isReal = mode === "real";
  const canExecute = isReal && dec && (dec.verdict === "buy" || dec.verdict === "sell") && dec.confidence >= 0.5;
  const decTone =
    dec?.verdict === "buy" ? "ok" : dec?.verdict === "sell" ? "rej" : "warn";

  return (
    <div className="agent-desk">
      <div className="agent-desk__head">
        <div>
          <h2>Agent Desk</h2>
          <p className="muted">
            Ciclo #{cycle.cycle_id} · {cycle.timestamp} · {cycle.paper_only ? "paper-only" : "live"}
            {cycle.team ? ` · time: ${cycle.team}` : ""}
          </p>
        </div>
        <div className={`agent-desk__decision agent-desk__decision--${decTone}`}>
          <span className="agent-desk__decision-label">DECISÃO</span>
          <span className="agent-desk__decision-verdict">{dec?.verdict.toUpperCase() ?? "—"}</span>
          <span className="agent-desk__decision-conf">conf {dec?.confidence.toFixed(2) ?? "0.00"}</span>
        </div>
        <button type="button" className="sig__real" onClick={load} disabled={loading}>
          ⟳ Rodar ciclo
        </button>
        <button
          type="button"
          className={loopRunning ? "btn btn--stop" : "btn btn--play"}
          onClick={toggleLoop}
          disabled={loopBusy || mode !== "real"}
          title={mode !== "real" ? "Loop requer modo REAL" : (loopRunning ? "Parar loop automático" : "Iniciar loop automático")}
        >
          {loopRunning ? "■ STOP" : "▶ PLAY"}
        </button>
        <button
          type="button"
          className="btn btn--reflect"
          onClick={reflectCycle}
          disabled={reflBusy || !cycle}
          title="Gerar reflexão dos trades do agente neste ciclo"
        >
          {reflBusy ? "Refletindo…" : "🪞 Reflect"}
        </button>
      </div>

      <div className="agent-desk__preset">
        <label htmlFor="preset">Preset do time (swarm)</label>
        <select
          id="preset"
          value={preset}
          onChange={(e) => { setPreset(e.target.value); load(); }}
        >
          {presets.map((p) => (
            <option key={p.name} value={p.name}>
              {SWARM_DESC[p.name] ?? p.name}
            </option>
          ))}
        </select>
        <span className="muted" style={{ fontSize: 11 }}>
          {presets.find((p) => p.name === preset)?.description ?? ""}
        </span>
      </div>

      <div className="agent-desk__playcfg">
        <span className="agent-desk__playcfg-title">Controles do PLAY</span>
        <div className="agent-desk__playcfg-grid">
          <label><span>SL %</span><input value={cfg.sl_pct} disabled={loopRunning} onChange={(e) => setCfg({ ...cfg, sl_pct: e.target.value })} /></label>
          <label><span>TP %</span><input value={cfg.tp_pct} disabled={loopRunning} onChange={(e) => setCfg({ ...cfg, tp_pct: e.target.value })} /></label>
          <label><span>Trailing %</span><input value={cfg.trailing_pct} disabled={loopRunning} onChange={(e) => setCfg({ ...cfg, trailing_pct: e.target.value })} /></label>
          <label><span>Meta ($)</span><input value={cfg.target_price} disabled={loopRunning} placeholder="ex: 64000" onChange={(e) => setCfg({ ...cfg, target_price: e.target.value })} /></label>
          <label className="agent-desk__toggle"><input type="checkbox" checked={cfg.auto_trade} disabled={loopRunning} onChange={(e) => setCfg({ ...cfg, auto_trade: e.target.checked })} /><span>Auto buy/sell</span></label>
          <label className="agent-desk__toggle"><input type="checkbox" checked={cfg.lock_stop} disabled={loopRunning} onChange={(e) => setCfg({ ...cfg, lock_stop: e.target.checked })} /><span>Lock Stop</span></label>
        </div>
        <span className="muted" style={{ fontSize: 11 }}>
          {cfg.auto_trade ? "Auto: executa ordens quando conf≥0.5." : "Análise only: PLAY não executa — use Executar ordem."}
          {cfg.lock_stop ? " Lock Stop: sem SL; só sai na Meta." : ""}
        </span>
      </div>

      <div className="agent-desk__exec">
        {isReal ? (
          <button
            type="button"
            className="btn btn--execute"
            onClick={execute}
            disabled={!canExecute || executing}
            title={canExecute ? "Executar ordem via PaperEngine" : "Apenas REAL + buy/sell conf>=0.5"}
          >
            {executing ? "Executando…" : "⚡ Executar ordem"}
          </button>
        ) : (
          <span className="badge badge--warn">DEMO — sem execução</span>
        )}
        {execMsg && <span className="agent-desk__exec-msg">{execMsg}</span>}
        {isReal && !canExecute && (
          <span className="muted" style={{ fontSize: 11 }}>
            Execução requer decisão buy/sell com conf ≥ 0.5
          </span>
        )}
      </div>

      {cycle.agents.length > 0 ? (
        <div className="agent-desk__grid">
          {cycle.agents.map((a) => (
            <AgentCard key={a.name} a={a} />
          ))}
        </div>
      ) : (
        <p className="muted">Time sem agentes (apenas análise).</p>
      )}

      {reflOpen && (
        <div className="agent-desk__reflections">
          <div className="agent-desk__reflections-head">
            <h3>Reflection Agents</h3>
            <button type="button" className="btn btn--small" onClick={() => setReflOpen(false)}>Fechar</button>
          </div>
          {reflections.length === 0 ? (
            <p className="muted">Sem reflexões ainda. Rode o PLAY para gerar trades.</p>
          ) : (
            reflections.slice().reverse().map((r, i) => (
              <div key={i} className="reflection-card">
                <div className="reflection-card__meta">
                  ciclo #{r.cycle_id} · {r.total_trades} trades · {r.timestamp?.slice(0, 19)}
                </div>
                <ul className="reflection-card__insights">
                  {(r.insights ?? []).map((ins: string, j: number) => (
                    <li key={j}>{ins}</li>
                  ))}
                </ul>
                {(r.recommendations?.length ?? 0) > 0 && (
                  <div className="reflection-card__recs">
                    <strong>Recomendações:</strong>
                    <ul>{(r.recommendations ?? []).map((rec: string, k: number) => (<li key={k}>{rec}</li>))}</ul>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
