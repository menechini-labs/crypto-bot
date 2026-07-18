import { Link } from "react-router-dom";
import Sparkline from "./Sparkline";
import type { Strategy } from "./types";

interface Props {
  strategy: Strategy;
}

export default function StrategyCard({ strategy }: Props) {
  const hasMetrics = strategy.netProfitPct !== null && strategy.netProfitPct !== undefined;
  const pnlClass = (strategy.netProfitPct ?? 0) >= 0 ? "up" : "down";
  const analyzeLink = `/analyze?symbol=${strategy.symbol}&strategy=${strategy.id}`;

  const fmt = (v: number | null | undefined, digits = 2) =>
    v === null || v === undefined ? "—" : v.toFixed(digits);

  return (
    <div className="strat-card">
      <div className="strat-card-head">
        <h3 className="strat-card-name">{strategy.name}</h3>
        <span className="badge">{strategy.symbol}</span>
      </div>

      <div className="strat-card-meta">
        <span className="tf">{strategy.timeframe}</span>
        <span className="by">@{strategy.author}</span>
        {strategy.hasBacktest === false && <span className="badge badge-warn">Sem backtest</span>}
      </div>

      <Sparkline points={strategy.equityCurve} width={280} height={60} />

      {hasMetrics ? (
        <div className="kpis">
          <div>
            <small className="kpi-l">PnL</small>
            <span className={pnlClass}>
              {(strategy.netProfitPct ?? 0) >= 0 ? "+" : ""}
              {strategy.netProfitPct}%
            </span>
          </div>
          <div>
            <small className="kpi-l">Drawdown</small>
            <span>{fmt(strategy.maxDrawdownPct)}%</span>
          </div>
          <div>
            <small className="kpi-l">Sharpe</small>
            <span>{fmt(strategy.sharpeRatio)}</span>
          </div>
          <div>
            <small className="kpi-l">Win Rate</small>
            <span>{fmt(strategy.winRatePct)}%</span>
          </div>
        </div>
      ) : (
        <div className="kpis kpis-empty">
          <span className="muted">Métricas disponíveis após rodar backtest</span>
        </div>
      )}

      <div className="strat-card-foot">
        <Link to={analyzeLink} className="btn-primary">
          🔍 Analyze
        </Link>
        {strategy.forkUrl ? (
          <a
            href={strategy.forkUrl}
            className="btn-secondary"
            target="_blank"
            rel="noopener noreferrer"
          >
            Fork ↗
          </a>
        ) : (
          <span className="btn-secondary disabled">Fork</span>
        )}
      </div>
    </div>
  );
}
