import { useEffect, useState } from "react";
import AgentAnalysisCard from "./AgentAnalysisCard";
import { fetchExternalSources, runBacktest } from "./api";
import Sparkline from "./Sparkline";
import type { AnalysisResult, BacktestParams, BacktestReport } from "./types";

const INIT: BacktestParams = {
  regime: "lateral",
  strategy: "grid",
  n: 300,
  seed: 42,
  symbol: "BTCUSDT",
};

const REGIMES = ["lateral", "uptrend", "downtrend"];
const STRATEGIES = ["grid", "grid_dynamic", "combined", "baseline", "default", "llm"];

interface Props {
  onRun?: (params: BacktestParams) => void;
}

export default function BacktestRunner({ onRun }: Props) {
  const [params, setParams] = useState(INIT);
  const [result, setResult] = useState<BacktestReport | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [extBUrl, setExtBUrl] = useState<string | null>(null);

  useEffect(() => {
    fetchExternalSources()
      .then((s) => setExtBUrl(s.backtest))
      .catch(() => {});
  }, []);
  const [status, setStatus] = useState<"idle" | "running">("idle");
  const [error, setError] = useState<string | null>(null);

  const set = <K extends keyof BacktestParams>(k: K, v: BacktestParams[K]) =>
    setParams((p) => ({ ...p, [k]: v }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("running");
    setError(null);
    setResult(null);
    setAnalysis(null);
    if (onRun) onRun(params);
    try {
      const { report: r, analysis: a } = await runBacktest(params);
      setResult(r);
      setAnalysis(a);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erro ao executar backtest";
      setError(`Erro: ${msg}`);
    } finally {
      setStatus("idle");
    }
  };

  return (
    <form className="backtest-runner" onSubmit={submit}>
      <h2 className="bt-title">Rodar Backtest</h2>

      <div className="bt-form">
        <label>
          <span>Símbolo</span>
          <input value={params.symbol} onChange={(e) => set("symbol", e.target.value)} />
        </label>

        <label>
          <span>Regime</span>
          <select
            value={params.regime}
            onChange={(e) => set("regime", e.target.value as BacktestParams["regime"])}
          >
            {REGIMES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Estratégia</span>
          <select value={params.strategy} onChange={(e) => set("strategy", e.target.value)}>
            {STRATEGIES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Candles</span>
          <input
            type="number"
            min={50}
            max={2000}
            value={params.n}
            onChange={(e) => set("n", Number(e.target.value))}
          />
        </label>

        <label>
          <span>Seed</span>
          <input
            type="number"
            min={0}
            max={1_000_000}
            value={params.seed}
            onChange={(e) => set("seed", Number(e.target.value))}
          />
        </label>
      </div>

      <button type="submit" className="bt-run" disabled={status === "running"}>
        {status === "running" ? "Rodando..." : "Executar"}
      </button>

      {extBUrl && (
        <div style={{ marginTop: 16 }}>
          <a href={extBUrl} className="btn-secondary" target="_blank" rel="noopener noreferrer">
            Relatório Externo ↗
          </a>
        </div>
      )}

      {error && (
        <div className="bt-error" role="alert">
          <p>{error}</p>
        </div>
      )}

      {result && (
        <div className="bt-result" data-testid="bt-result">
          <h3>Resultado</h3>
          {analysis && <AgentAnalysisCard analysis={analysis} />}

          <div className="bt-kpis">
            <div className="kpi">
              <small>PnL</small>
              <span className={result.pnl_pct >= 0 ? "up" : "down"}>
                {(result.pnl_pct * 100).toFixed(1)}%
              </span>
            </div>
            <div className="kpi">
              <small>PnL $</small>
              <span className={result.pnl_pct >= 0 ? "up" : "down"}>${result.pnl.toFixed(2)}</span>
            </div>
            <div className="kpi">
              <small>Drawdown</small>
              <span>{(result.max_drawdown_pct * 100).toFixed(1)}%</span>
            </div>
            <div className="kpi">
              <small>Sharpe</small>
              <span>{result.sharpe.toFixed(2)}</span>
            </div>
            {result.sharpe_ci && (
              <div className="kpi" style={{ gridColumn: "span 2" }}>
                <small>Sharpe 95% CI</small>
                <span className="muted">
                  [{result.sharpe_ci[0]?.toFixed(2) ?? "N/A"},{" "}
                  {result.sharpe_ci[1]?.toFixed(2) ?? "N/A"}]
                </span>
              </div>
            )}
            <div className="kpi">
              <small>Win Rate</small>
              <span>{result.win_rate.toFixed(0)}%</span>
            </div>
            <div className="kpi">
              <small>Turnover</small>
              <span>{((result.turnover ?? 0) * 100).toFixed(1)}%</span>
            </div>
            <div className="kpi">
              <small>Trades</small>
              <span>{result.trades}</span>
            </div>
            <div className="kpi">
              <small>CAGR</small>
              <span>{result.cagr.toFixed(1)}%</span>
            </div>
            <div className="kpi">
              <small>Equity Final</small>
              <span>${result.final_equity.toFixed(2)}</span>
            </div>
          </div>

          {result.equity_curve && result.equity_curve.length > 1 && (
            <div className="bt-chart">
              <h4>Equity Curve</h4>
              <Sparkline points={result.equity_curve} width={500} height={120} />
            </div>
          )}
        </div>
      )}
    </form>
  );
}
