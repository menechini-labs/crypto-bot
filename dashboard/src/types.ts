export interface PositionInfo {
  qty: number;
  avg_price: number;
}

export interface EquityPoint {
  cycle: number;
  equity: number;
  pnl: number;
  positions: Record<string, PositionInfo>;
}

export interface PortfolioStats {
  lastEquity: number;
  lastPnl: number;
  maxDrawdown: number;
}

export type DashboardState =
  | { status: "loading" }
  | { status: "loaded"; data: EquityPoint[] }
  | { status: "error"; error: string };
