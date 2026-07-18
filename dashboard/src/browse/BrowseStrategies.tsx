import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchStrategies, fetchExternalSources } from "./api";
import BacktestRunner from "./BacktestRunner";
import FiltersBar from "./FiltersBar";
import StrategyCard from "./StrategyCard";
import type { Strategy } from "./types";

const INIT_FILTERS: Record<string, string | number> = {
  symbol: "",
  timeframe: "",
  minPnl: "",
  maxDd: "",
  minSharpe: "",
  author: "",
};

export default function BrowseStrategies() {
  const [all, setAll] = useState<Strategy[]>([]);
  const [filters, setFilters] = useState<Record<string, string | number>>(INIT_FILTERS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [extBrowse, setExtBrowse] = useState<string | null>(null);

  function refresh() {
    (async () => {
      try {
        setLoading(true);
        const data = await fetchStrategies();
        setAll(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Erro ao carregar estrategias");
      } finally {
        setLoading(false);
      }
    })();
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 30_000);
    fetchExternalSources().then(s => setExtBrowse(s.browse)).catch(() => {}); // refresh a cada 30s
    return () => clearInterval(interval);
  }, []);

  const filtered = useMemo(() => {
    let list = all;
    if (filters.symbol)
      list = list.filter((s) => s.symbol === filters.symbol);
    if (filters.timeframe)
      list = list.filter((s) => s.timeframe === filters.timeframe);
    if (filters.minPnl !== "" && filters.minPnl !== undefined) {
      const v = Number(filters.minPnl);
      if (!isNaN(v)) list = list.filter((s) => s.netProfitPct !== null && s.netProfitPct >= v);
    }
    if (filters.maxDd !== "" && filters.maxDd !== undefined) {
      const v = Number(filters.maxDd);
      if (!isNaN(v)) list = list.filter((s) => s.maxDrawdownPct !== null && s.maxDrawdownPct <= v);
    }
    if (filters.minSharpe !== "" && filters.minSharpe !== undefined) {
      const v = Number(filters.minSharpe);
      if (!isNaN(v)) list = list.filter((s) => s.sharpeRatio !== null && s.sharpeRatio >= v);
    }
    if (filters.author) list = list.filter((s) => s.author === filters.author);
    return list;
  }, [all, filters]);

  const clearFilters = () => setFilters(INIT_FILTERS);

  if (loading)
    return <div className="loading" role="status">Carregando estratégias...</div>;
  if (error)
    return (
      <div className="error" role="alert">
        <p>{error}</p>
        <button onClick={() => window.location.reload()} className="btn-secondary">
          Tentar novamente
        </button>
      </div>
    );

  return (
    <div className="browse-page">
      <header className="browse-header">
        <h1 className="browse-title">Browse Estratégias</h1>
        <div className="browse-actions">
          <button className="btn-secondary" onClick={refresh} title="Recarregar">⟳</button>
          <Link to="/analyze" className="btn-primary">+ Novo Backtest</Link>
          {extBrowse && (
            <a href={extBrowse} className="btn-secondary" target="_blank" rel="noopener noreferrer">
              Browse Externo ↗
            </a>
          )}
        </div>
      </header>

      <FiltersBar current={filters} onChange={setFilters} onClear={clearFilters} />

      <section className="browse-body" aria-label="Resultados">
        <p className="result-count">{filtered.length} estratégia(s) encontrada(s)</p>
        <div className="grid">
          {filtered.map((s) => (
            <StrategyCard key={s.id} strategy={s} />
          ))}
        </div>
      </section>

      <BacktestRunner onRun={() => {}} />
    </div>
  );
}
