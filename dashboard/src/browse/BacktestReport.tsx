import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import AgentAnalysisCard from "./AgentAnalysisCard";
import { fetchBacktestReport, runBacktest, triggerBacktestReflection } from "./api";
import Sparkline from "./Sparkline";
import type { AnalysisResult, BacktestParams, BacktestReport as ReportData } from "./types";

export default function BacktestReport() {
  const { id = "" } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [report, setReport] = useState<ReportData | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [reflecting, setReflecting] = useState(false);
  const [reflection, setReflection] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"view" | "run">("view");

  useEffect(() => {
    if (!id) return;
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchBacktestReport(id);
        setReport(data.report);
        setAnalysis(data.analysis);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Erro ao carregar relatório");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  async function handleReflection() {
    if (!id) return;
    setReflecting(true);
    try {
      const ref = await triggerBacktestReflection(id);
      setReflection(ref);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro na reflexão");
    } finally {
      setReflecting(false);
    }
  }

  async function handleRun(params: BacktestParams) {
    try {
      setLoading(true);
      setError(null);
      const result = await runBacktest(params);
      setReport(result.report);
      setAnalysis(result.analysis);
      setReflection(null);
      const newId = result.report.id;
      window.history.replaceState(null, "", `/backtest/${newId}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao rodar backtest");
    } finally {
      setLoading(false);
    }
  }

  if (!id) {
    return (
      <div className="report-empty">
        <h2>Backtest Report</h2>
        <p>Selecione uma estratégia no Browse ou rode um backtest.</p>
        <BacktestRunnerForm onRun={handleRun} />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="report-loading" role="status" aria-label="Carregando relatório">
        <div className="spinner" />
        <p>Carregando backtest...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="report-error" role="alert">
        <h2>Erro ao carregar</h2>
        <p>{error}</p>
        <button onClick={() => navigate("/browse")}>Voltar ao Browse</button>
        <button onClick={() => setMode("run")}>Rodar novo backtest</button>
        {mode === "run" && (
          <BacktestRunnerForm onRun={handleRun} onCancel={() => setMode("view")} />
        )}
      </div>
    );
  }

  if (!report) return null;

  const pnlClass = report.pnl_pct >= 0 ? "pos" : "neg";
  const ddClass = report.max_drawdown_pct > 20 ? "neg" : report.max_drawdown_pct > 10 ? "pos" : "";

  return (
    <article className="report-view">
      <header className="report-header">
        <Link to="/browse" className="back-link">
          ← Browse
        </Link>
        <Link to="/" className="back-link back-link-home">
          ⌂ Home
        </Link>
        <h1 className="report-title">
          {report.symbol} / {report.strategy}
        </h1>
        <span className={`report-badge ${report.regime}`}>{report.regime}</span>
        <div className="report-actions">
          <button className="bt-run" onClick={() => setMode(mode === "run" ? "view" : "run")}>
            {mode === "run" ? "Fechar" : "Novo backtest"}
          </button>
          <button className="bt-reflection" onClick={handleReflection} disabled={reflecting}>
            {reflecting ? "Analisando..." : "🔍 Reflection Agent"}
          </button>
        </div>
      </header>

      {mode === "run" && <BacktestRunnerForm onRun={handleRun} onCancel={() => setMode("view")} />}

      {/* Agent Analysis Card */}
      {analysis && <AgentAnalysisCard analysis={analysis} />}

      {/* Reflection result */}
      {reflection && (
        <section className="reflection-panel">
          <h2>🧠 Reflexão do Agent</h2>
          <div className="reflection-metrics">
            <div>
              <small>Trades</small>
              <span>{String(reflection.total_trades ?? "—")}</span>
            </div>
            <div>
              <small>Win Rate</small>
              <span>
                {reflection.metrics
                  ? `${((reflection.metrics as Record<string, number>).win_rate * 100).toFixed(0)}%`
                  : "—"}
              </span>
            </div>
            <div>
              <small>Max Perdas Consecutivas</small>
              <span>
                {reflection.metrics
                  ? String(
                      (reflection.metrics as Record<string, number>).max_consecutive_losses ?? 0,
                    )
                  : "—"}
              </span>
            </div>
          </div>
          {Array.isArray(reflection.insights) && reflection.insights.length > 0 && (
            <ul className="reflection-insights">
              {(reflection.insights as string[]).slice(0, 5).map((i, idx) => (
                <li key={idx}>{i}</li>
              ))}
            </ul>
          )}
          {Array.isArray(reflection.recommendations) && reflection.recommendations.length > 0 && (
            <div className="reflection-recs">
              <h4>Recomendações</h4>
              <ul>
                {(reflection.recommendations as string[]).slice(0, 3).map((r, idx) => (
                  <li key={idx}>{r}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {/* KPIs */}
      <section className="report-kpis" aria-label="Métricas principais">
        <div className="kpi-card">
          <span className="kpi-label">PnL Total</span>
          <span className={`kpi-value ${pnlClass}`}>
            {report.pnl_pct >= 0 ? "+" : ""}
            {report.pnl_pct.toFixed(2)}%
          </span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Max Drawdown</span>
          <span className={`kpi-value ${ddClass}`}>{report.max_drawdown_pct.toFixed(2)}%</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Win Rate</span>
          <span className="kpi-value">{report.win_rate.toFixed(1)}%</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Sharpe</span>
          <span className="kpi-value">{report.sharpe.toFixed(2)}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">CAGR</span>
          <span className="kpi-value">{report.cagr.toFixed(1)}%</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Trades</span>
          <span className="kpi-value">{report.trades}</span>
        </div>
      </section>

      {/* Chart */}
      {report.equity_curve && report.equity_curve.length > 0 && (
        <section className="report-chart" aria-label="Curva de equity">
          <h2>Equity Curve</h2>
          <Sparkline points={report.equity_curve} width={800} height={300} />
          <p className="chart-caption">
            {report.equity_curve.length} candles · Início: ${report.equity.toFixed(2)} · Fim: $
            {report.final_equity.toFixed(2)}
          </p>
        </section>
      )}

      {/* Details */}
      <section className="report-details" aria-label="Detalhes">
        <h2>Detalhes</h2>
        <dl className="details-grid">
          <div>
            <dt>Símbolo</dt>
            <dd>{report.symbol}</dd>
          </div>
          <div>
            <dt>Estratégia</dt>
            <dd>{report.strategy}</dd>
          </div>
          <div>
            <dt>Regime</dt>
            <dd>{report.regime}</dd>
          </div>
          <div>
            <dt>Candles</dt>
            <dd>{report.candles}</dd>
          </div>
          <div>
            <dt>Seed</dt>
            <dd>{report.seed}</dd>
          </div>
          <div>
            <dt>Capital Inicial</dt>
            <dd>${report.equity.toFixed(2)}</dd>
          </div>
          <div>
            <dt>Capital Final</dt>
            <dd>${report.final_equity.toFixed(2)}</dd>
          </div>
          <div>
            <dt>PnL Absoluto</dt>
            <dd className={pnlClass}>${report.pnl.toFixed(2)}</dd>
          </div>
          <div>
            <dt>Profit Factor</dt>
            <dd>{report.profit_factor?.toFixed(2) ?? "N/A"}</dd>
          </div>
          <div>
            <dt>Sortino</dt>
            <dd>{report.sortino?.toFixed(2) ?? "N/A"}</dd>
          </div>
          <div>
            <dt>Calmar</dt>
            <dd>{report.calmar?.toFixed(2) ?? "N/A"}</dd>
          </div>
        </dl>
      </section>

      {/* Trades table */}
      {report.trades_list && report.trades_list.length > 0 && (
        <section className="report-trades" aria-label="Lista de trades">
          <h2>Trades ({report.trades_list.length})</h2>
          <div className="trades-table-wrap">
            <table className="trades-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Tipo</th>
                  <th>Entrada</th>
                  <th>Saída</th>
                  <th>PnL</th>
                  <th>PnL%</th>
                  <th>Duração</th>
                </tr>
              </thead>
              <tbody>
                {report.trades_list.slice(0, 50).map((t, i) => (
                  <tr key={i}>
                    <td>{i + 1}</td>
                    <td className={t.side === "buy" ? "side-buy" : "side-sell"}>{t.side}</td>
                    <td>${t.entry_price.toFixed(2)}</td>
                    <td>${t.exit_price.toFixed(2)}</td>
                    <td className={t.pnl >= 0 ? "up" : "down"}>${t.pnl.toFixed(2)}</td>
                    <td className={t.pnl_pct >= 0 ? "up" : "down"}>
                      {t.pnl_pct >= 0 ? "+" : ""}
                      {t.pnl_pct.toFixed(2)}%
                    </td>
                    <td>{t.duration_min}min</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {report.trades_list.length > 50 && (
              <p className="trades-truncated">Mostrando 50 de {report.trades_list.length} trades</p>
            )}
          </div>
        </section>
      )}

      <footer className="report-footer">
        <p>Gerado em {new Date(report.timestamp).toLocaleString("pt-BR")}</p>
        <p>Fonte: {report.source ?? "local"}</p>
      </footer>
    </article>
  );
}

/* ---- inline runner form ---- */
function BacktestRunnerForm({
  onRun,
  onCancel,
}: {
  onRun: (p: BacktestParams) => void;
  onCancel?: () => void;
}) {
  const REGIMES = ["lateral", "uptrend", "downtrend"];
  const STRATEGIES = ["grid", "grid_dynamic", "combined", "baseline", "default"];
  const [params, setParams] = useState<BacktestParams>({
    regime: "lateral",
    strategy: "grid",
    n: 300,
    seed: 42,
    symbol: "BTCUSDT",
  });
  const [status, setStatus] = useState<"idle" | "running">("idle");

  const set = <K extends keyof BacktestParams>(k: K, v: BacktestParams[K]) => {
    setParams((p) => ({ ...p, [k]: v }));
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("running");
    await onRun(params);
    setStatus("idle");
  };

  return (
    <form className="backtest-form-inline" onSubmit={submit}>
      <h3>Rodar novo backtest</h3>
      <div className="form-row">
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
      <div className="form-action">
        <button type="submit" className="bt-run" disabled={status === "running"}>
          {status === "running" ? "Rodando..." : "Executar"}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} className="btn-secondary">
            Cancelar
          </button>
        )}
      </div>
    </form>
  );
}
