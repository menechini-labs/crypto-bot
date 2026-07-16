import type { BrowseFilters } from "./data";

interface Props {
  filters: BrowseFilters;
  onChange: (f: BrowseFilters) => void;
}

/**
 * Barra de filtros horizontal – réplica do design StrategyFactory.
 */
export default function FiltersBar({ filters, onChange }: Props) {
  const set = (key: keyof BrowseFilters, val: string) => {
    onChange({ ...filters, [key]: val });
  };

  return (
    <form className="filters" onSubmit={(e) => e.preventDefault()}>
      <select
        className="filter-select"
        value={filters.symbol}
        onChange={(e) => set("symbol", e.target.value)}
      >
        <option value="">All pairs</option>
        <option value="BTCUSDT">BTCUSDT</option>
        <option value="ETHUSDT">ETHUSDT</option>
        <option value="SOLUSDT">SOLUSDT</option>
        <option value="DOGEUSDT">DOGEUSDT</option>
        <option value="BNBUSDT">BNBUSDT</option>
        <option value="AVAXUSDT">AVAXUSDT</option>
        <option value="LINKUSDT">LINKUSDT</option>
        <option value="XRPUSDT">XRPUSDT</option>
      </select>
      <input
        className="filter-input tf"
        type="text"
        placeholder="TF — 1h"
        value={filters.timeframe}
        onChange={(e) => set("timeframe", e.target.value)}
      />
      <input
        className="filter-input numeric"
        type="number"
        step={0.1}
        placeholder="Min P&L %"
        title="Minimum net profit %"
        value={filters.minPnl}
        onChange={(e) => set("minPnl", e.target.value)}
      />
      <input
        className="filter-input numeric"
        type="number"
        step={0.1}
        min={0}
        placeholder="Min PF"
        title="Minimum profit factor"
        value={filters.minPf}
        onChange={(e) => set("minPf", e.target.value)}
      />
      <input
        className="filter-input numeric"
        type="number"
        step={0.1}
        placeholder="Min Sharpe"
        value={filters.minSharpe}
        onChange={(e) => set("minSharpe", e.target.value)}
      />
      <input
        className="filter-input numeric"
        type="number"
        step={0.1}
        placeholder="Min Sortino"
        value={filters.minSortino}
        onChange={(e) => set("minSortino", e.target.value)}
      />
      <input
        className="filter-input numeric"
        type="number"
        step={1}
        min={0}
        max={100}
        placeholder="Min Win %"
        value={filters.minWinRate}
        onChange={(e) => set("minWinRate", e.target.value)}
      />
      <input
        className="filter-input numeric"
        type="number"
        step={0.1}
        min={0}
        placeholder="Max DD %"
        value={filters.maxDD}
        onChange={(e) => set("maxDD", e.target.value)}
      />
      <input
        className="filter-input numeric"
        type="number"
        step={1}
        min={0}
        placeholder="Min Trades"
        value={filters.minTrades}
        onChange={(e) => set("minTrades", e.target.value)}
      />
    </form>
  );
}
