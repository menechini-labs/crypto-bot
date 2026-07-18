const SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"];
const TIMEFRAMES = ["1h", "4h", "1d"];

interface Props {
  current: Record<string, string | number>;
  onChange: (f: Record<string, string | number>) => void;
  onClear: () => void;
}

export default function FiltersBar({ current, onChange, onClear }: Props) {
  const set = (k: string, v: string | number) => {
    onChange({ ...current, [k]: v });
  };

  return (
    <div className="filters" role="search" aria-label="Filtros de estratégias">
      <label>
        <span>Símbolo</span>
        <select
          value={String(current.symbol || "")}
          onChange={(e) => set("symbol", e.target.value)}
        >
          <option value="">Todos</option>
          {SYMBOLS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>

      <label>
        <span>Timeframe</span>
        <select
          value={String(current.timeframe || "")}
          onChange={(e) => set("timeframe", e.target.value)}
        >
          <option value="">Todos</option>
          {TIMEFRAMES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </label>

      <button className="btn-secondary" onClick={onClear}>
        Limpar filtros
      </button>
    </div>
  );
}
