export interface Strategy {
  id: string;
  name: string;
  symbol: string;
  timeframe: string;
  author: string;
  netProfitPct: number;
  profitFactor: number;
  maxDrawdownPct: number;
  winRatePct: number;
  sharpeRatio: number;
  sortinoRatio: number;
  totalTrades: number;
  equityCurve: number[];
  forkUrl: string;
}

export interface BacktestParams {
  regime: "lateral" | "uptrend" | "downtrend";
  strategy: string;
  n: number;
  seed: number;
  symbol: string;
}

export interface BacktestResult {
  pnl_pct: number;
  max_drawdown_pct: number;
  win_rate: number;
  sharpe: number;
  cagr: number;
  trades_final: number;
  trades: number;
  final_equity: number;
  equity: number;
  equityCurve: number[];
  regime: string;
  seed: number;
  n: number;
  symbol: string;
  strategy: string;
}

export interface Trade {
  side: "buy" | "sell";
  entry_price: number;
  exit_price: number;
  pnl: number;
  pnl_pct: number;
  duration_min: number;
}

export interface BacktestReport {
  id: string;
  symbol: string;
  strategy: string;
  regime: string;
  timeframe: string;
  candles: number;
  seed: number;
  equity: number;
  final_equity: number;
  pnl: number;
  pnl_pct: number;
  max_drawdown_pct: number;
  win_rate: number;
  sharpe: number;
  cagr: number;
  trades: number;
  profit_factor?: number;
  sortino?: number;
  calmar?: number;
  equity_curve: number[];
  trades_list?: Trade[];
  timestamp: string;
  source?: string;
}

export interface AnalysisResult {
  assessment: "ok" | "warn" | "alert";
  sharpe: number;
  cagr: number;
  max_dd: number;
  win_rate: number;
  summary: string;
}
