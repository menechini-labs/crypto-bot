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

export interface ScoreComponents {
  trend: number;
  momentum: number;
  volatility: number;
  risk_reward: number;
  regime: number;
}

export interface ScoreDetails {
  components: ScoreComponents;
  regime: string;
  rsi: number;
  volatility_pct: number;
  risk_reward_ratio: number;
  weights: Record<string, number>;
}

export interface ScoreSignal {
  signal: string;
  confidence: number;
  risk_score: number;
  composite: number;
  details: ScoreDetails;
}

export interface SignalScoreResponse {
  status: string;
  signal: string;
  score: ScoreSignal;
  explanation: string;
  llm_enabled?: boolean;
}

export interface Reflection {
  source: string;
  cycle_id: number;
  total_trades: number;
  timestamp?: string;
  insights: string[];
  recommendations?: string[];
  metrics?: Record<string, unknown>;
}
