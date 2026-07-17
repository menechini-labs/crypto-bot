import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { runBacktest } from "./api";
import BacktestRunner from "./BacktestRunner";
import type { BacktestReport, AnalysisResult, Trade } from "./types";

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return { ...actual, runBacktest: vi.fn() };
});

const mockTrades: Trade[] = [
  { side: "buy", entry_price: 100, exit_price: 104, pnl: 4, pnl_pct: 0.04, duration_min: 60 },
  { side: "buy", entry_price: 104, exit_price: 101, pnl: -3, pnl_pct: -0.0288, duration_min: 90 },
];

const mockReport: BacktestReport = {
  id: "btc_grid_lateral_42",
  symbol: "BTCUSDT",
  strategy: "grid",
  regime: "lateral",
  timeframe: "1h",
  candles: 300,
  seed: 42,
  equity: 1000,
  final_equity: 1113.03,
  pnl: 113.03,
  pnl_pct: 0.113,
  max_drawdown_pct: 0.035,
  win_rate: 0.2727,
  sharpe: 7.55,
  cagr: 22.14,
  trades: 11,
  equity_curve: [100, 102, 105, 103, 108],
  trades_list: mockTrades,
  timestamp: "2025-01-01T00:00:00Z",
  source: "local",
};

const mockAnalysis: AnalysisResult = {
  assessment: "ok",
  sharpe: 7.55,
  cagr: 22.14,
  max_dd: 0.035,
  win_rate: 0.2727,
  summary: "Bom desempenho, baixo risco.",
};

describe("BacktestRunner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renderiza formulario com campos padrao", () => {
    render(<BacktestRunner />);
    expect(screen.getByRole("heading", { name: "Rodar Backtest" })).toBeTruthy();
    expect(screen.getByDisplayValue("BTCUSDT")).toBeTruthy();
    expect(screen.getByDisplayValue("300")).toBeTruthy();
  });

  it("chama onRun apos submit", async () => {
    const onRun = vi.fn();
    vi.mocked(runBacktest).mockResolvedValue({ report: mockReport, analysis: mockAnalysis });

    render(<BacktestRunner onRun={onRun} />);
    fireEvent.click(screen.getByText("Executar"));

    await waitFor(() => {
      expect(onRun).toHaveBeenCalledTimes(1);
    });
    expect(onRun).toHaveBeenCalledWith(
      expect.objectContaining({ regime: "lateral", strategy: "grid", n: 300, seed: 42 }),
    );
  });

  it("exibe resultado apos backtest bem sucedido", async () => {
    vi.mocked(runBacktest).mockResolvedValue({ report: mockReport, analysis: mockAnalysis });

    render(<BacktestRunner />);
    fireEvent.click(screen.getByText("Executar"));

    await waitFor(() => {
      expect(screen.getByText("Resultado")).toBeTruthy();
    });
  });

  it("exibe erro quando runBacktest falha", async () => {
    vi.mocked(runBacktest).mockRejectedValue(new Error("API error"));

    render(<BacktestRunner />);
    fireEvent.click(screen.getByText("Executar"));

    await waitFor(() => {
      expect(screen.getByText(/Erro/)).toBeTruthy();
    });
  });

  it("filtros alteram estado do formulario", () => {
    render(<BacktestRunner />);

    const regimeSelect = screen.getByDisplayValue("lateral");
    fireEvent.change(regimeSelect, { target: { value: "uptrend" } });
    expect(screen.getByDisplayValue("uptrend")).toBeTruthy();

    const candleInput = screen.getByDisplayValue("300");
    fireEvent.change(candleInput, { target: { value: "500" } });
    expect(screen.getByDisplayValue("500")).toBeTruthy();
  });
});
