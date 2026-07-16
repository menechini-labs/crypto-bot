import { useEffect, useMemo, useState } from "react";
import type { BrowseFilters, StrategyResult } from "./data";
import { generateMockStrategies } from "./data";
import FiltersBar from "./FiltersBar";
import StrategyCard from "./StrategyCard";

/* estado dos filtros */
const INIT_FILTERS: BrowseFilters = {
  symbol: "",
  timeframe: "",
  minPnl: "",
  minPf: "",
  minSharpe: "",
  minSortino: "",
  minWinRate: "",
  maxDD: "",
  minTrades: "",
};

function applyFilters(list: StrategyResult[], f: BrowseFilters): StrategyResult[] {
  return list.filter((s) => {
    if (f.symbol && s.symbol !== f.symbol) return false;
    if (f.timeframe && s.timeframe !== f.timeframe) return false;
    if (f.minPnl && s.netProfitPct < Number.parseFloat(f.minPnl)) return false;
    if (f.minPf) {
      const minPf = Number.parseFloat(f.minPf);
      if (s.profitFactor != null && s.profitFactor < minPf) return false;
      if (s.profitFactor == null && minPf > 10) return false; // PF infinity treated as very high
    }
    if (f.minSharpe && s.sharpeRatio < Number.parseFloat(f.minSharpe)) return false;
    if (f.minSortino && s.sortinoRatio < Number.parseFloat(f.minSortino)) return false;
    if (f.minWinRate && s.winRatePct < Number.parseFloat(f.minWinRate)) return false;
    if (f.maxDD && s.maxDrawdownPct > Number.parseFloat(f.maxDD)) return false;
    if (f.minTrades && s.totalTrades < Number.parseInt(f.minTrades, 10)) return false;
    return true;
  });
}

/**
 * Aba "Browse Strategies" – grid de cards com filtros.
 * Dados mock (simula API /strategies/search).
 */
export default function BrowseStrategies() {
  const [filters, setFilters] = useState<BrowseFilters>(INIT_FILTERS);
  const [all, setAll] = useState<StrategyResult[]>([]);

  useEffect(() => {
    // Simula fetch com delay pra ver loading state
    const t = setTimeout(() => setAll(generateMockStrategies(36)), 300);
    return () => clearTimeout(t);
  }, []);

  const filtered = useMemo(() => applyFilters(all, filters), [all, filters]);

  return (
    <div className="browse-page">
      <div className="browse-header">
        <h1 className="browse-title">Browse Strategies</h1>
        <p className="browse-sub">
          {all.length} estratégias simuladas. Filtre por KPI para encontrar padrões.
        </p>
      </div>

      <div className="stats-banner">
        <div className="stat">
          <span className="stat-num">{all.length}</span>
          <span className="stat-label">Estratégias</span>
        </div>
      </div>

      <FiltersBar filters={filters} onChange={setFilters} />

      {all.length === 0 ? (
        <div className="loading" style={{ marginTop: "2rem" }}>
          Carregando estratégias...
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty" style={{ marginTop: "2rem" }}>
          Nenhuma estratégia encontrada com estes filtros.
        </div>
      ) : (
        <div className="grid">
          {filtered.map((s) => (
            <StrategyCard key={s.id} strategy={s} />
          ))}
        </div>
      )}
    </div>
  );
}
