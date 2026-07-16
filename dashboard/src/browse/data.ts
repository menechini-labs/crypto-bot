/**
 * Dados mock multi-par para a aba Browse.
 * Inspirado na API /strategies/search do StrategyFactory.
 */
export interface StrategyResult {
  id: string;
  name: string;
  symbol: string;
  timeframe: string;
  author: string;
  netProfitPct: number;
  profitFactor: number | null;
  maxDrawdownPct: number;
  winRatePct: number;
  sharpeRatio: number;
  sortinoRatio: number;
  totalTrades: number;
  /** Equity preview (índice = ciclo, valor = equity normalizada 0..1) */
  equityCurve: number[];
}

/* Helper: gera spark série random walk realista */
function randEquity(n: number, drift = 0.002, vol = 0.04): number[] {
  const pts: number[] = [1];
  for (let i = 1; i < n; i++) {
    const r = pts[i - 1] * (1 + drift + (Math.random() - 0.5) * vol);
    pts.push(r);
  }
  // normalizar 0..1
  const mn = Math.min(...pts);
  const mx = Math.max(...pts);
  const span = mx - mn || 1;
  return pts.map((p) => (p - mn) / span);
}

/* Gera um lote de estratégias mock */
export function generateMockStrategies(count = 36): StrategyResult[] {
  const symbols = [
    { sym: "BTCUSDT", px: 62500 },
    { sym: "ETHUSDT", px: 3450 },
    { sym: "SOLUSDT", px: 142 },
    { sym: "DOGEUSDT", px: 0.12 },
    { sym: "BNBUSDT", px: 580 },
    { sym: "AVAXUSDT", px: 35 },
    { sym: "LINKUSDT", px: 14 },
    { sym: "XRPUSDT", px: 0.52 },
  ];
  const tfs = ["1m", "5m", "15m", "1h", "4h", "D"];
  const names = [
    "Grid Dynamic %s",
    "Grid Static %s",
    "Trend Follow %s",
    "Mean Reversion %s",
    "RSI Divergence %s",
    "MACD Cross %s",
    "Bollinger Squeeze %s",
    "ADX Breakout %s",
    "Supertrend %s",
    "Scalp %s",
    "EMA Crossover %s",
    "VWAP Revert %s",
  ];
  const authors = [
    "Eduardo S.",
    "CryptoWhale",
    "satoshi_nakamoto",
    "AlgoTrader42",
    "DeFi Wizard",
    "QuantBrasil",
  ];

  const list: StrategyResult[] = [];

  for (let i = 0; i < count; i++) {
    const s = symbols[i % symbols.length];
    const tf = tfs[i % tfs.length];
    const name = names[i % names.length].replace("%s", s.sym);
    const author = authors[i % authors.length];

    // Gera métricas realistas mas variadas
    const netPct = (Math.random() - 0.28) * 120; // -28% a +86%
    const pf = netPct > 0 ? 1.0 + Math.random() * 3.5 : 0.2 + Math.random() * 1.0;
    const winRate = 30 + Math.random() * 55;
    const trades = 5 + Math.floor(Math.random() * 250);
    const maxDD = 5 + Math.random() * 45;
    const sharpe = (netPct > 0 ? 0.1 : -0.3) + Math.random() * 1.5;
    const sortino = sharpe * (0.5 + Math.random() * 0.8);
    const equityLen = 20 + Math.floor(Math.random() * 60);
    const eqDrift = netPct > 0 ? 0.003 : -0.002;
    const eqVol = 0.03 + Math.random() * 0.05;

    list.push({
      id: `strat_${i}_${Date.now()}`,
      name,
      symbol: s.sym,
      timeframe: tf,
      author,
      netProfitPct: Math.round(netPct * 100) / 100,
      profitFactor: pf > 99 ? null : Math.round(pf * 100) / 100,
      maxDrawdownPct: Math.round(maxDD * 100) / 100,
      winRatePct: Math.round(winRate * 100) / 100,
      sharpeRatio: Math.round(sharpe * 100) / 100,
      sortinoRatio: Math.round(sortino * 100) / 100,
      totalTrades: trades,
      equityCurve: randEquity(equityLen, eqDrift, eqVol),
    });
  }

  return list;
}

export interface BrowseFilters {
  symbol: string;
  timeframe: string;
  minPnl: string;
  minPf: string;
  minSharpe: string;
  minSortino: string;
  minWinRate: string;
  maxDD: string;
  minTrades: string;
}
