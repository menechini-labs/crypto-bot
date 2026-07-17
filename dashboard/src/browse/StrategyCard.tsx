import type { Strategy } from "./types";
import Sparkline from "./Sparkline";
import { Link } from "react-router-dom";

interface Props {
  strategy: Strategy;
}

export default function StrategyCard({ strategy }: Props) {
  const pnlClass = strategy.netProfitPct >= 0 ? "up" : "down";
  const analyzeLink = `/analyze?symbol=${strategy.symbol}&strategy=${strategy.id}`;

  return (
    <div className="strat-card">
      <div className="strat-card-head">
        <h3 className="strat-card-name">{strategy.name}</h3>
        <span className="badge">{strategy.symbol}</span>
      </div>

      <div className="strat-card-meta">
        <span>{strategy.author}</span>
        <span>{strategy.timeframe}</span>
      </div>

      <Sparkline points={strategy.equityCurve} width={280} height={60} />

      <div className="kpis">
        <div>
          <small className="kpi-l">PnL</small>
          <span className={pnlClass}>{strategy.netProfitPct >= 0 ? "+" : ""}{strategy.netProfitPct}%</span>
        </div>
        <div>
          <small className="kpi-l">Drawdown</small>
          <span>{strategy.maxDrawdownPct}%</span>
        </div>
        <div>
          <small className="kpi-l">Sharpe</small>
          <span>{strategy.sharpeRatio.toFixed(2)}</span>
        </div>
        <div>
          <small className="kpi-l">Win Rate</small>
          <span>{strategy.winRatePct}%</span>
        </div>
      </div>

      <div className="strat-card-foot">
        <Link to={analyzeLink} className="btn-primary">
          🔍 Analyze
        </Link>
        <a href={strategy.forkUrl} className="btn-secondary" target="_blank" rel="noopener noreferrer">
          Fork ↗
        </a>
      </div>
    </div>
  );
}
