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

export default function AgentDesk() {
  const [cycle, setCycle] = useState<Cycle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/agents/cycle");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setCycle((await res.json()) as Cycle);
    } catch (e) {
      setError(e instanceof Error ? e.message : "erro ao carregar agentes");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
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

      <div className="agent-desk__grid">
        {cycle.agents.map((a) => (
          <AgentCard key={a.name} a={a} />
        ))}
      </div>
    </div>
  );
}
