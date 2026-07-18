# Phase 4 Plan — Polish (sidebar + mode badge + connection status + a11y)

Companion to `frontend-daytrader-architecture.md` + Phase 0/1/2/3 plans.
Goal: unified sidebar navigation, paper/live toggle (paper-locked), connection
status probe, basic a11y (`aria-current`, `aria-label`).

**STATUS: DONE (2026-07-17)**

## Done
- **Sidebar** (`Dashboard.tsx` + `index.css`): left 248px column with nav groups
  (Overview / Markets / Intelligence / Execution), brand "Signal Terminal · day-trader desk".
  Group labels + icon per item. ` aria-current="page"` on active nav button.
- **Paper/live toggle**: pinned "PAPER (locked)" badge at bottom. Mode is
  always `"paper"` via `useState` — no toggle (MVP locked). Styled mode-badge
  (yellow for paper, green for live).
- **Connection status**: probes `/api/health` every 15s;
  shows "conectando...", "API online", or "API offline" with green/red/neutral dot.
- **Responsive**: `<720px` sidebar hidden, grid collapses to single column.
- **Template**: `<div className="app app--sidebar">`, `<main>` with header + content.
- CSS: removed `.tabs`/`.tab` in favor of sidebar nav. All existing tabs preserved
  (dashboard/browse/scoring/analyze/health/agents/news/tradedesk).

## Notas / próximos
- Phase 4 conclui as 5 fases do plano arquitetural `frontend-daytrader-architecture.md`.
- Próximo: `external_sources.py` integração (mcp-api), exchangeInfo validation,
  ledger persistence, `/bmad_spec` (SPEC.md), restart gateway p/ BMAD skills.
