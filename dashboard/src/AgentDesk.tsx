import { useEffect, useState } from "react";

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
  agents: AgentRecord[];
  decision: AgentRecord;
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

  async function loadPresets() {
    try {
      const res = await fetch("/api/swarm-presets");
      if (res.ok) setPresets((await res.json()) as SwarmPreset[]);
    } catch {
      /* silencioso */
    }
  }

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/agents/cycle?team=${encodeURIComponent(preset)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setCycle((await res.json()) as Cycle);
    } catch (e) {
      setError(e instanceof Error ? e.message : "erro ao carregar agentes");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPresets();
    load();
    const id = setInterval(load, 30_000);
    return () => clearInterval(id);
  }, []);

  if (error) return <div className="error" role="alert">{error}</div>;
  if (!cycle) return <div className="loading">Carregando Agent Desk…</div>;

  const dec = cycle.decision;
  const decTone =
    dec.verdict === "buy" ? "ok" : dec.verdict === "sell" ? "rej" : "warn";

  return (
    <div className="agent-desk">
      <div className="agent-desk__head">
        <div>
          <h2>Agent Desk</h2>
          <p className="muted">
            Ciclo #{cycle.cycle_id} · {cycle.timestamp} · {cycle.paper_only ? "paper-only" : "live"}
          </p>
        </div>
        <div className={`agent-desk__decision agent-desk__decision--${decTone}`}>
          <span className="agent-desk__decision-label">DECISÃO</span>
          <span className="agent-desk__decision-verdict">{dec.verdict.toUpperCase()}</span>
          <span className="agent-desk__decision-conf">conf {dec.confidence.toFixed(2)}</span>
        </div>
        <button type="button" className="sig__real" onClick={load} disabled={loading}>
          ⟳ Rodar ciclo
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

      <div className="agent-desk__grid">
        {cycle.agents.map((a) => (
          <AgentCard key={a.name} a={a} />
        ))}
      </div>
    </div>
  );
}
