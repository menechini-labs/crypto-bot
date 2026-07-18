import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AgentDesk from "../AgentDesk";

// Mock monaco editor (heavy) and charts so we render the controls only.
vi.mock("@monaco-editor/react", () => ({
  default: () => <textarea data-testid="mock-editor" />,
}));
vi.mock("react-echarts", () => ({
  default: () => <div data-testid="mock-chart" />,
}));

beforeEach(() => {
  vi.stubGlobal("fetch", (url: string) => {
    const ok = (data: unknown) => Promise.resolve({ ok: true, json: () => Promise.resolve(data) });
    if (url.includes("/api/agents/loop/status")) {
      return ok({ status: "ok", running: false, team: "balanced", symbol: "BTCUSDT", interval: 20, mode: "demo" });
    }
    if (url.includes("/api/agents/reflections")) {
      return ok({ status: "ok", reflections: [] });
    }
    if (url.includes("/api/config/mode")) {
      return ok({ mode: "demo" });
    }
    if (url.includes("/api/swarm-presets")) {
      return ok([{ name: "balanced", description: "time balanceado" }]);
    }
    // cycle + presets
    return ok({
      cycle_id: 123,
      regime: "trend",
      decision: { verdict: "hold", confidence: 0.5, reasoning: "ok" },
      agents: [],
      score: { total: 0.5, components: {} },
    });
  });
});

describe("AgentDesk PLAY controls + Reflect", () => {
  it("renders PLAY controls (SL/TP/Trailing/Meta/Auto/Lock) and Reflect button", async () => {
    render(<AgentDesk />);
    await waitFor(() => expect(screen.getByText("Controles do PLAY")).toBeTruthy());
    expect(screen.getByLabelText("SL %")).toBeTruthy();
    expect(screen.getByLabelText("TP %")).toBeTruthy();
    expect(screen.getByLabelText("Trailing %")).toBeTruthy();
    expect(screen.getByLabelText("Meta ($)")).toBeTruthy();
    expect(screen.getByText("Auto buy/sell")).toBeTruthy();
    expect(screen.getByText("Lock Stop")).toBeTruthy();
    expect(screen.getByText(/Reflect/)).toBeTruthy();
  });

  it("PLAY button is disabled in demo mode", async () => {
    render(<AgentDesk />);
    await waitFor(() => expect(screen.getByText("▶ PLAY")).toBeTruthy());
    const play = screen.getByText("▶ PLAY").closest("button") as HTMLButtonElement;
    expect(play.disabled).toBe(true);
  });
});
