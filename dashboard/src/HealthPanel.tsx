import { useEffect, useState } from "react";
import { apiGet, ApiError } from "./api";

interface Health {
  status: string;
  time: string;
  version: string;
  llm_enabled: boolean;
  registry_strategies: string[];
  scoring_available: boolean;
  indicators_available: boolean;
}

interface Metrics {
  status: string;
  metrics: Record<string, number>;
  ts: string;
}

interface RiskState {
  status: string;
  config: Record<string, number>;
  metrics: Record<string, number>;
  paper_only: boolean;
}

export default function HealthPanel() {
  const [health, setHealth] = useState<Health | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [risk, setRisk] = useState<RiskState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [h, m, r] = await Promise.all([
          apiGet<Health>("/api/health"),
          apiGet<Metrics>("/api/metrics"),
          apiGet<RiskState>("/api/risk/state"),
        ]);
        setHealth(h);
        setMetrics(m);
        setRisk(r);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : "erro ao carregar health");
      }
    })();
  }, []);

  if (error) return <div className="error" role="alert">{error}</div>;
  if (!health || !metrics || !risk) return <div className="loading">Carregando status…</div>;

  return (
    <div className="health-panel">
      <h2>System Health</h2>

      <section className="health-card">
        <h3>Backend</h3>
        <dl className="details-grid">
          <div><dt>Status</dt><dd>{health.status}</dd></div>
          <div><dt>Versão</dt><dd>{health.version}</dd></div>
          <div><dt>LLM</dt><dd>{health.llm_enabled ? "habilitado" : "desligado"}</dd></div>
          <div><dt>Scoring</dt><dd>{health.scoring_available ? "ok" : "n/a"}</dd></div>
          <div><dt>Indicators</dt><dd>{health.indicators_available ? "ok" : "n/a"}</dd></div>
        </dl>
        <p className="muted">Estratégias no registry: {health.registry_strategies.join(", ")}</p>
      </section>

      <section className="health-card">
        <h3>Risk Guard (paper-only)</h3>
        <dl className="details-grid">
          {Object.entries(risk.config).map(([k, v]) => (
            <div key={k}><dt>{k}</dt><dd>{v}</dd></div>
          ))}
        </dl>
        <p className="muted">Rejeições de risco: {risk.metrics.risk_rejections} · Ordens paper: {risk.metrics.orders_paper}</p>
      </section>

      <section className="health-card">
        <h3>Metrics</h3>
        <dl className="details-grid">
          {Object.entries(metrics.metrics).map(([k, v]) => (
            <div key={k}><dt>{k}</dt><dd>{v}</dd></div>
          ))}
        </dl>
      </section>
    </div>
  );
}
