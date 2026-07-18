import { useEffect, useState } from "react";
import BrowseStrategies from "./browse/BrowseStrategies";
import EquityChart from "./EquityChart";
import StatCard from "./StatCard";
import ScorePanel from "./ScorePanel";
import AnalyzePage from "./browse/AnalyzePage";
import HealthPanel from "./HealthPanel";
import AgentDesk from "./AgentDesk";
import NewsFeed from "./NewsFeed";
import TradeDesk from "./TradeDesk";
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

/* === tabs === */

type Tab = "dashboard" | "browse" | "scoring" | "analyze" | "health" | "agents" | "news" | "tradedesk";

interface NavItem {
  id: Tab;
  label: string;
  icon: string;
  group: string;
}

const NAV: NavItem[] = [
  { id: "dashboard", label: "Dashboard", icon: "◧", group: "Overview" },
  { id: "browse", label: "Browse", icon: "⌕", group: "Overview" },
  { id: "scoring", label: "Scoring", icon: "✦", group: "Markets" },
  { id: "analyze", label: "Analyze", icon: "◎", group: "Markets" },
  { id: "agents", label: "Agents", icon: "⚇", group: "Intelligence" },
  { id: "news", label: "News", icon: "❏", group: "Intelligence" },
  { id: "health", label: "Health", icon: "♥", group: "Intelligence" },
  { id: "tradedesk", label: "Trade Desk", icon: "⤬", group: "Execution" },
];

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

/* === DashboardTab (conteúdo original) === */

function DashboardTab({ state, lastCycle }: { state: DashboardState; lastCycle: number }) {
  if (state.status === "loading") {
    return (
      <div className="loading" style={{ marginTop: "2rem" }}>
        Carregando...
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="error" style={{ marginTop: "1.5rem" }}>
        Erro: {state.error}
      </div>
    );
  }

  const { data } = state;
  const stats = computeStats(data);
  const pnlTone = stats.lastPnl >= 0 ? "pos" : "neg";
  const positions = data.length > 0 ? data[data.length - 1].positions : {};

  return (
    <>
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
    </>
  );
}

/* === componente principal === */

export default function Dashboard() {
  const { state, lastCycle } = useEquity();
  const [tab, setTab] = useState<Tab>("dashboard");
  const [mode] = useState<"paper" | "live">("paper"); // live locked — MVP paper-only
  const [connected, setConnected] = useState<boolean | null>(null);

  // Connection status probe
  useEffect(() => {
    let active = true;
    const probe = async () => {
      try {
        const res = await fetch("/api/health");
        if (active) setConnected(res.ok);
      } catch {
        if (active) setConnected(false);
      }
    };
    probe();
    const id = setInterval(probe, 15000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  const groups = Array.from(new Set(NAV.map((n) => n.group)));

  return (
    <div className="app app--sidebar">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <div className="logo">₿</div>
          <div>
            <strong>Signal Terminal</strong>
            <p>day-trader desk</p>
          </div>
        </div>

        <nav className="sidebar__nav" aria-label="Navegação principal">
          {groups.map((g) => (
            <div className="nav-group" key={g}>
              <span className="nav-group__label">{g}</span>
              {NAV.filter((n) => n.group === g).map((n) => (
                <button
                  key={n.id}
                  type="button"
                  aria-current={tab === n.id ? "page" : undefined}
                  className={`nav-item ${tab === n.id ? "nav-item--active" : ""}`}
                  onClick={() => setTab(n.id)}
                >
                  <span className="nav-item__icon" aria-hidden="true">{n.icon}</span>
                  <span>{n.label}</span>
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar__foot">
          <div className={`mode-badge mode-badge--${mode}`}>
            <span className="mode-badge__dot" /> {mode === "paper" ? "PAPER (locked)" : "LIVE"}
          </div>
          <div className={`conn-status conn-status--${connected === null ? "unknown" : connected ? "up" : "down"}`}>
            <span className="conn-status__dot" />
            {connected === null ? "conectando..." : connected ? "API online" : "API offline"}
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="header">
          <div className="brand">
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

        {tab === "dashboard" && <DashboardTab state={state} lastCycle={lastCycle} />}
        {tab === "browse" && <BrowseStrategies />}
        {tab === "scoring" && <ScorePanel />}
        {tab === "analyze" && <AnalyzePage />}
        {tab === "health" && <HealthPanel />}
        {tab === "agents" && <AgentDesk />}
        {tab === "news" && <NewsFeed />}
        {tab === "tradedesk" && <TradeDesk />}
      </main>
    </div>
  );
}
