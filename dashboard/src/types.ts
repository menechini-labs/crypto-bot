export interface EquityPoint {
  cycle: number;
  equity: number;
  pnl: number;
  positions: Record<string, { qty: number; avg_price: number }>;
}

export interface PortfolioStats {
  lastEquity: number;
  lastPnl: number;
  maxDrawdown: number;
  sharpe: number;
}
