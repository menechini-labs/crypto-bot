import { useEffect, useState } from "react";
import EquityChart from "./EquityChart";
import StatCard from "./StatCard";
import type { DashboardState, EquityPoint, PortfolioStats } from "./types";

/* === helpers === */

function fmtUsd(v: number): string {
  const sign = v >= 0 ? "+" : "-";
  return `${sign}$${Math.abs(v).toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
}

function computeStats(data: EquityPoint[]): PortfolioStats {
  if (data.length === 0) {
    return { lastEquity: 0, lastPnl: 0, maxDrawdown: 0 };
  }
  const last = data[data.length - 1];
  let peak = data[0].equity;
  let maxDd = 0;
  for (const p of data) {
    if (p.equity > peak) peak = p.equity;
    const dd = peak > 0 ? (peak - p.equity) / peak : 0;
    if (dd > maxDd) maxDd = dd;
  }
  return { lastEquity: last.equity, lastPnl: last.pnl, maxDrawdown: maxDd };
}

/* === custom hook (react-patterns: encapsula estado + efeito) === */

function useEquity() {
  const [state, setState] = useState<DashboardState>({ status: "loading" });
  const [lastCycle, setLastCycle] = useState(0);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const res = await fetch("/equity");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = (await res.json()) as EquityPoint[];
        if (!active) return;
        setState({ status: "loaded", data: json });
        if (json.length > 0) setLastCycle(json[json.length - 1].cycle);
      } catch (e) {
        if (active) {
          const msg = e instanceof Error ? e.message : "erro desconhecido";
          setState({ status: "error", error: msg });
        }
      }
    };
    load();
    const id = setInterval(load, 5000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  return { state, lastCycle };
}

/* === componente principal === */

export default function Dashboard() {
  const { state, lastCycle } = useEquity();

  if (state.status === "loading") {
    return (
      <div className="app">
        <header className="header">
          <div className="brand">
            <div className="logo">₿</div>
            <div className="brand__titles">
              <h1>Crypto Bot</h1>
              <p>Paper trading · spot</p>
            </div>
          </div>
        </header>
        <div className="loading">Carregando...</div>
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="app">
        <header className="header">
          <div className="brand">
            <div className="logo">₿</div>
            <div className="brand__titles">
              <h1>Crypto Bot</h1>
              <p>Paper trading · spot</p>
            </div>
          </div>
        </header>
        <div className="error">Erro ao carregar: {state.error}</div>
      </div>
    );
  }

  /* loaded */
  const { data } = state;
  const stats = computeStats(data);
  const pnlTone = stats.lastPnl >= 0 ? "pos" : "neg";
  const positions = data.length > 0 ? data[data.length - 1].positions : {};

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <div className="logo">₿</div>
          <div className="brand__titles">
            <h1>Crypto Bot</h1>
            <p>Paper trading · spot · sem risco real</p>
          </div>
        </div>
        <div className="status">
          <span className="dot" />
          ciclo #{lastCycle} · atualizado
        </div>
      </header>

      <section className="cards">
        <StatCard
          label="Equity"
          value={`$${stats.lastEquity.toLocaleString("en-US", { maximumFractionDigits: 2 })}`}
        />
        <StatCard
          label="PnL"
          value={fmtUsd(stats.lastPnl)}
          tone={pnlTone}
          sub={data.length > 0 ? `ciclo #${lastCycle}` : "—"}
        />
        <StatCard
          label="Max Drawdown"
          value={`${(stats.maxDrawdown * 100).toFixed(2)}%`}
          tone={stats.maxDrawdown > 0.1 ? "neg" : "neutral"}
        />
        <StatCard label="Posições" value={`${Object.keys(positions).length}`} sub="ativos" />
      </section>

      <section className="panel">
        <h2>Equity ao longo dos ciclos</h2>
        <EquityChart points={data.map((d) => d.equity)} />
      </section>

      <section className="panel">
        <h2>Posições atuais</h2>
        {Object.keys(positions).length === 0 ? (
          <p className="empty">Nenhuma posição aberta.</p>
        ) : (
          <table className="positions">
            <thead>
              <tr>
                <th>Ativo</th>
                <th>Qtd</th>
                <th>Preço médio</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(positions).map(([sym, pos]) => (
                <tr key={sym}>
                  <td>{sym}</td>
                  <td>{pos.qty}</td>
                  <td>${pos.avg_price.toLocaleString("en-US", { maximumFractionDigits: 2 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
