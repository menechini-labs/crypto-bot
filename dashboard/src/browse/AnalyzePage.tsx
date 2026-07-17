import { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { runBacktest, triggerBacktestReflection } from "./api";
import AgentAnalysisCard from "./AgentAnalysisCard";
import Sparkline from "./Sparkline";
import type { BacktestParams, BacktestReport as ReportData, AnalysisResult, Trade } from "./types";

const REGIMES = ["lateral", "uptrend", "downtrend"];
const STRATEGIES = ["grid", "grid_dynamic", "combined", "baseline", "default", "llm"];

export default function AnalyzePage() {
  const [searchParams] = useSearchParams();
  const initSymbol = searchParams.get("symbol") || "BTCUSDT";
  // Strategy card IDs are like "grid_dynamic_eth"; the backend expects the base
  // strategy name ("grid_dynamic"). Map the known prefixes and strip the
  // "_<SYMBOL>" suffix so the backtest request validates.
  const initStrategy =
    searchParams
      .get("strategy")
      ?.replace(/^grid_static_.*/, "grid")
      .replace(/^grid_dynamic_.*/, "grid_dynamic")
      .replace(/^trend_follow_.*/, "default") || "grid";

  const [symbol, setSymbol] = useState(initSymbol);
  const [strategy, setStrategy] = useState(initStrategy);
  const [regime, setRegime] = useState("lateral");
  const [candles, setCandles] = useState(300);
  const [seed, setSeed] = useState(42);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<ReportData | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [reflection, setReflection] = useState<Record<string, unknown> | null>(null);
  const [reflecting, setReflecting] = useState(false);

  // auto-match strategy id from url
  useEffect(() => {
    setSymbol(initSymbol);
    setStrategy(initStrategy);
  }, [initSymbol, initStrategy]);

  function reset() {
    setReport(null);
    setAnalysis(null);
    setReflection(null);
    setError(null);
  }

  async function handleRun() {
    reset();
    setLoading(true);
    try {
      const payload: BacktestParams = {
        symbol,
        strategy,
        regime: regime as BacktestParams["regime"],
        n: candles,
        seed,
      };
      const { report: r, analysis: a } = await runBacktest(payload);
      setReport(r);
      setAnalysis(a);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao rodar backtest");
    } finally {
      setLoading(false);
    }
  }

  async function handleReflection() {
    if (!report?.id) return;
    setReflecting(true);
    try {
      const ref = await triggerBacktestReflection(report.id);
      setReflection(ref);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro na reflexão");
    } finally {
      setReflecting(false);
    }
  }

  return (
    <div className="analyze-page">
      <header className="analyze-header">
        <Link to="/browse" className="back-link">← Browse</Link>
        <h1>🔍 Analyze Crypto</h1>
      </header>

      {/* Formulário */}
      <section className="analyze-form">
        <div className="form-row">
          <label>
            <span>Symbol</span>
            <input value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} />
          </label>
          <label>
            <span>Strategy</span>
            <select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
              {STRATEGIES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
          <label>
            <span>Regime</span>
            <select value={regime} onChange={(e) => setRegime(e.target.value)}>
              {REGIMES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </label>
          <label>
            <span>Candles</span>
            <input type="number" min={50} max={2000} value={candles} onChange={(e) => setCandles(Number(e.target.value))} />
          </label>
          <label>
            <span>Seed</span>
            <input type="number" min={0} max={1_000_000} value={seed} onChange={(e) => setSeed(Number(e.target.value))} />
          </label>
        </div>
        <button className="bt-run" onClick={handleRun} disabled={loading}>
          {loading ? "Running..." : "Run Backtest"}
        </button>
      </section>

      {error && <div className="error" role="alert">{error}</div>}

      {/* Agent Analysis */}
      {analysis && (
        <section className="analyze-agent">
          <h2>Agent Analysis</h2>
          <AgentAnalysisCard analysis={analysis} />
          <button className="bt-reflection" onClick={handleReflection} disabled={reflecting}>
            {reflecting ? "Analyzing..." : "🧠 Reflection Agent"}
          </button>
        </section>
      )}

      {/* Reflection */}
      {reflection && (
        <section className="reflection-panel">
          <h3>🧠 Reflection</h3>
          <div className="reflection-metrics">
            <div><small>Trades</small><span>{String(reflection.total_trades ?? "—")}</span></div>
            <div><small>Win Rate</small><span>{reflection.metrics ? `${((reflection.metrics as Record<string, number>).win_rate * 100).toFixed(0)}%` : "—"}</span></div>
            <div><small>Max Consec Loss</small><span>{reflection.metrics ? String((reflection.metrics as Record<string, number>).max_consecutive_losses ?? 0) : "—"}</span></div>
          </div>
          {Array.isArray(reflection.insights) && (
            <ul>{(reflection.insights as string[]).slice(0, 5).map((i, idx) => <li key={idx}>{i}</li>)}</ul>
          )}
          {Array.isArray(reflection.recommendations) && (
            <div>
              <h4>Recommendations</h4>
              <ul>{(reflection.recommendations as string[]).slice(0, 3).map((r, idx) => <li key={idx}>{r}</li>)}</ul>
            </div>
          )}
        </section>
      )}

      {/* Report */}
      {report && (
        <section className="analyze-report">
          <h2>Report: {report.symbol} / {report.strategy}</h2>

          <div className="report-kpis">
            <div className="kpi-card"><span className="kpi-label">PnL</span><span className={`kpi-value ${report.pnl_pct >= 0 ? "pos" : "neg"}`}>{report.pnl_pct >= 0 ? "+" : ""}{report.pnl_pct.toFixed(2)}%</span></div>
            <div className="kpi-card"><span className="kpi-label">Max DD</span><span className="kpi-value">{report.max_drawdown_pct.toFixed(2)}%</span></div>
            <div className="kpi-card"><span className="kpi-label">Win Rate</span><span className="kpi-value">{report.win_rate.toFixed(1)}%</span></div>
            <div className="kpi-card"><span className="kpi-label">Sharpe</span><span className="kpi-value">{report.sharpe.toFixed(2)}</span></div>
            <div className="kpi-card"><span className="kpi-label">CAGR</span><span className="kpi-value">{report.cagr.toFixed(1)}%</span></div>
            <div className="kpi-card"><span className="kpi-label">Trades</span><span className="kpi-value">{report.trades}</span></div>
          </div>

          {report.equity_curve && report.equity_curve.length > 0 && (
            <div className="report-chart">
              <h3>Equity Curve</h3>
              <Sparkline points={report.equity_curve} width={800} height={250} />
            </div>
          )}

          <div className="report-details">
            <dl className="details-grid">
              <div><dt>Symbol</dt><dd>{report.symbol}</dd></div>
              <div><dt>Strategy</dt><dd>{report.strategy}</dd></div>
              <div><dt>Regime</dt><dd>{report.regime}</dd></div>
              <div><dt>Seed</dt><dd>{report.seed}</dd></div>
              <div><dt>Candles</dt><dd>{report.candles}</dd></div>
              <div><dt>Initial</dt><dd>${report.equity.toFixed(2)}</dd></div>
              <div><dt>Final</dt><dd>${report.final_equity.toFixed(2)}</dd></div>
            </dl>
          </div>

          {report.trades_list && report.trades_list.length > 0 && (
            <div className="report-trades">
              <h3>Trades ({report.trades_list.length})</h3>
              <div className="trades-table-wrap">
                <table className="trades-table">
                  <thead>
                    <tr><th>#</th><th>Side</th><th>Entry</th><th>Exit</th><th>PnL</th><th>PnL%</th><th>Dur</th></tr>
                  </thead>
                  <tbody>
                    {report.trades_list.slice(0, 50).map((t: Trade, i: number) => (
                      <tr key={i}>
                        <td>{i + 1}</td>
                        <td>{t.side}</td>
                        <td>${t.entry_price.toFixed(2)}</td>
                        <td>${t.exit_price.toFixed(2)}</td>
                        <td className={t.pnl >= 0 ? "up" : "down"}>${t.pnl.toFixed(2)}</td>
                        <td className={t.pnl_pct >= 0 ? "up" : "down"}>{t.pnl_pct >= 0 ? "+" : ""}{t.pnl_pct.toFixed(2)}%</td>
                        <td>{t.duration_min}min</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <footer className="report-footer">
            <p>{new Date(report.timestamp).toLocaleString("pt-BR")} · source: {report.source ?? "local"}</p>
          </footer>
        </section>
      )}
    </div>
  );
}
