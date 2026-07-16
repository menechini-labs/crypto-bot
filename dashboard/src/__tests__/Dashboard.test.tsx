import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Dashboard from "../Dashboard";
import type { EquityPoint } from "../types";

// mock do fetch retornando payload padrao
const sample: EquityPoint[] = [
  { cycle: 1, equity: 1000, pnl: 0, positions: {} },
  { cycle: 2, equity: 1010, pnl: 10, positions: {} },
  {
    cycle: 3,
    equity: 1025,
    pnl: 25,
    positions: { "BTC/USDT": { qty: 0.01, avg_price: 60000 } },
  },
];

describe("Dashboard", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("renderiza titulo e estatisticas apos fetch", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => sample,
      } as Response),
    );

    render(<Dashboard />);

    // titulo estatico
    expect(screen.getByText(/crypto bot/i)).toBeTruthy();

    // apos fetch, mostra equity do ultimo ponto
    await waitFor(() => {
      expect(screen.getByText(/\$1,025/)).toBeTruthy();
    });

    // mostra PnL positivo
    await waitFor(() => {
      expect(screen.getByText(/\+\$25/)).toBeTruthy();
    });

    // lista posicao
    await waitFor(() => {
      expect(screen.getByText(/BTC\/USDT/)).toBeTruthy();
    });
  });

  it("mostra mensagem de erro se fetch falhar", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network")));
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText(/erro ao carregar/i)).toBeTruthy();
    });
  });
});
