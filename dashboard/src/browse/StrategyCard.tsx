import type { StrategyResult } from "./data";
import Sparkline from "./Sparkline";

interface Props {
  strategy: StrategyResult;
}

function fmtPct(v: number): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

function fmtNum(v: number, d = 2): string {
  return v.toFixed(d);
}

/**
 * Card de estratégia – réplica do design StrategyFactory.
 */
export default function StrategyCard({ strategy }: Props) {
  const { name, symbol, timeframe, author, netProfitPct } = strategy;
  const pf = strategy.profitFactor;
  const lr = strategy;

  const netClass = netProfitPct >= 0 ? "kpi-v up" : "kpi-v down";

  return (
    <div className="strat-card">
      <div className="strat-card-head">
        <div className="strat-card-name">{name}</div>
        <div className="strat-card-meta">
          <span className="sym">{symbol}</span>
          <span className="tf">{timeframe}</span>
        </div>
      </div>

      <Sparkline points={strategy.equityCurve} />

      <div className="kpis">
        <div className="kpi">
          <span className="kpi-l">Net Profit</span>
          <span className={netClass}>{fmtPct(netProfitPct)}</span>
        </div>
        <div className="kpi">
          <span className="kpi-l">PF</span>
          <span className="kpi-v">{pf != null ? fmtNum(pf) : "∞"}</span>
        </div>
        <div className="kpi">
          <span className="kpi-l">Max DD</span>
          <span className="kpi-v">{fmtPct(lr.maxDrawdownPct)}</span>
        </div>
        <div className="kpi">
          <span className="kpi-l">Win Rate</span>
          <span className="kpi-v">{fmtNum(lr.winRatePct, 0)}%</span>
        </div>
        <div className="kpi">
          <span className="kpi-l">Sharpe</span>
          <span className="kpi-v">{fmtNum(lr.sharpeRatio)}</span>
        </div>
        <div className="kpi">
          <span className="kpi-l">Sortino</span>
          <span className="kpi-v">{fmtNum(lr.sortinoRatio)}</span>
        </div>
        <div className="kpi">
          <span className="kpi-l">Trades</span>
          <span className="kpi-v">{lr.totalTrades}</span>
        </div>
      </div>

      <div className="strat-card-foot">
        <div className="strat-card-author">
          <span className="ava">{(author[0] || "A").toUpperCase()}</span>
          <span className="name">@{author}</span>
        </div>
        <div className="badge-container">
          <span className="badge badge-fork">Fork</span>
        </div>
      </div>
    </div>
  );
}
