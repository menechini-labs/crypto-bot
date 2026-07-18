import { useEffect, useState } from "react";

interface Position {
  id: string;
  symbol: string;
  side: string;
  qty: number;
  entry_price: number;
  mark_price: number;
  stop_loss: number | null;
  take_profit: number | null;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
}

interface Snapshot {
  cash: number;
  equity: number;
  positions: Position[];
  open_orders: number;
  total_orders: number;
  paper_only: boolean;
  exits: Array<{ symbol: string; reason: string }>;
  demo?: boolean;
}

export default function TradeDesk({ mode }: { mode: "demo" | "real" }) {
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [qty, setQty] = useState("0.001");
  const [sl, setSl] = useState("");
  const [tp, setTp] = useState("");
  const [trail, setTrail] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const demo = mode === "demo";

  async function refresh() {
    try {
      const res = await fetch("/api/positions");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setSnap((await res.json()) as Snapshot);
    } catch (e) {
      setError(e instanceof Error ? e.message : "erro ao carregar posições");
    }
  }

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 15_000);
    return () => clearInterval(id);
  }, []);

  async function submit(side: "buy" | "sell") {
    if (demo) return;
    setMsg(null);
    setError(null);
    try {
      const res = await fetch("/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: symbol.toUpperCase(),
          side,
          qty: Number(qty),
          sl_pct: sl ? Number(sl) : null,
          tp_pct: tp ? Number(tp) : null,
          trailing_pct: trail ? Number(trail) : null,
        }),
      });
      const j = await res.json();
      if (!res.ok || !j.ok) {
        setError(j.error || `HTTP ${res.status}`);
      } else {
        setMsg(`${side.toUpperCase()} paper executado em ${j.order?.id ?? ""}`);
        refresh();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "erro ao enviar ordem");
    }
  }

  return (
    <div className="trade-desk">
      <div className="trade-desk__head">
        <h2>Trade Desk <span className="badge-warn">PAPER</span></h2>
        <p className="muted">Simulação only — nenhuma ordem real. Fill a preço de mercado Binance.</p>
      </div>

      <div className="trade-desk__panel">
        <div className="trade-desk__summary">
          <div className="td-stat"><small>Caixa</small><span>${snap?.cash.toFixed(2) ?? "—"}</span></div>
          <div className="td-stat"><small>Equity</small><span>${snap?.equity.toFixed(2) ?? "—"}</span></div>
          <div className="td-stat"><small>Posições</small><span>{snap?.positions.length ?? 0}</span></div>
          <div className="td-stat"><small>Ordens</small><span>{snap?.total_orders ?? 0}</span></div>
        </div>

        {snap?.exits && snap.exits.length > 0 && (
          <div className="trade-desk__exits">
            {snap.exits.map((x, i) => (
              <span key={i} className="td-exit">⚡ {x.symbol} {x.reason}</span>
            ))}
          </div>
        )}

        <form className="trade-desk__form" onSubmit={(e) => e.preventDefault()}>
          <label><span>Símbolo</span><input value={symbol} onChange={(e) => setSymbol(e.target.value)} /></label>
          <label><span>Qtd</span><input value={qty} onChange={(e) => setQty(e.target.value)} /></label>
          <label><span>SL %</span><input value={sl} placeholder="ex: 0.05" onChange={(e) => setSl(e.target.value)} /></label>
          <label><span>TP %</span><input value={tp} placeholder="ex: 0.10" onChange={(e) => setTp(e.target.value)} /></label>
          <label><span>Trailing %</span><input value={trail} placeholder="ex: 0.03" onChange={(e) => setTrail(e.target.value)} /></label>
          <div className="trade-desk__actions">
            {demo ? (
              <p className="td-msg td-msg--warn">DEMO mode · execução desligada. Ative REAL no menu lateral.</p>
            ) : (
              <>
                <button type="button" className="td-buy" onClick={() => submit("buy")}>BUY (paper)</button>
                <button type="button" className="td-sell" onClick={() => submit("sell")}>SELL (paper)</button>
              </>
            )}
          </div>
        </form>

        {msg && <p className="td-msg td-msg--ok">{msg}</p>}
        {error && <p className="td-msg td-msg--err">Erro: {error}</p>}
      </div>

      <div className="trade-desk__positions">
        <h3>Posições abertas</h3>
        {!snap?.positions.length && <p className="muted">Nenhuma posição paper.</p>}
        <table className="td-table">
          <thead>
            <tr><th>Símbolo</th><th>Lado</th><th>Qtd</th><th>Entrada</th><th>Mark</th><th>SL</th><th>TP</th><th>uPNL</th><th>%</th></tr>
          </thead>
          <tbody>
            {snap?.positions.map((p) => (
              <tr key={p.id}>
                <td>{p.symbol}</td>
                <td>{p.side}</td>
                <td>{p.qty}</td>
                <td>{p.entry_price}</td>
                <td>{p.mark_price}</td>
                <td>{p.stop_loss ?? "—"}</td>
                <td>{p.take_profit ?? "—"}</td>
                <td className={p.unrealized_pnl >= 0 ? "pos" : "neg"}>{p.unrealized_pnl}</td>
                <td className={p.unrealized_pnl_pct >= 0 ? "pos" : "neg"}>{p.unrealized_pnl_pct}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
