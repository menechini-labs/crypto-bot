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
    <div className="strategy-card">
      <div className="card-header">
        <h3 className="card-name">{strategy.name}</h3>
        <span className="card-badge">{strategy.symbol}</span>
      </div>

      <div className="card-meta">
        <span>{strategy.author}</span>
        <span>{strategy.timeframe}</span>
      </div>

      <Sparkline points={strategy.equityCurve} width={280} height={60} />

      <div className="card-stats">
        <div>
          <small>PnL</small>
          <span className={pnlClass}>{strategy.netProfitPct >= 0 ? "+" : ""}{strategy.netProfitPct}%</span>
        </div>
        <div>
          <small>Drawdown</small>
          <span>{strategy.maxDrawdownPct}%</span>
        </div>
        <div>
          <small>Sharpe</small>
          <span>{strategy.sharpeRatio.toFixed(2)}</span>
        </div>
        <div>
          <small>Win Rate</small>
          <span>{strategy.winRatePct}%</span>
        </div>
      </div>

      <div className="card-footer">
        <Link to={analyzeLink} className="btn-primary analyze-link">
          🔍 Analyze
        </Link>
        <a href={strategy.forkUrl} className="btn-secondary fork-link" target="_blank" rel="noopener noreferrer">
          Fork ↗
        </a>
      </div>
    </div>
  );
}
