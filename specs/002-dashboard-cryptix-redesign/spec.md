# Feature Specification: Dashboard Cryptix Redesign

**Feature Branch**: `[feature/dashboard-cryptix-redesign]`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Redesign/improve the crypto-bot frontend inspired by the Cryptix template (Framer Community Marketplace: https://www.framer.com/community/marketplace/templates/cryptix/)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Modernized dashboard landing (Priority: P1)

A user opens the dashboard and sees a polished, modern crypto-portfolio interface
inspired by the Cryptix design language: clean layout, generous spacing, rounded
cards with soft shadows, strong typography, and a coherent color theme. All existing
information (portfolio equity, P&L, max drawdown, equity curve) is preserved and
presented more clearly.

**Why this priority**: This is the first screen users see and the primary value
surface. A modern visual layer directly addresses the request to "improve the
frontend" without changing backend behavior.

**Independent Test**: Can be verified by loading the dashboard in a browser and
confirming all current equity/portfolio data still renders, now within the new
visual shell. Delivers a visibly upgraded UI with no loss of information.

**Acceptance Scenarios**:

1. **Given** the dashboard is loaded, **When** the user views the portfolio section, **Then** equity, P&L, and max-drawdown are displayed with the new card/theme treatment.
2. **Given** the new theme, **When** the user compares old vs new, **Then** spacing, rounding, shadows, and typography follow a single coherent design language (no mixed styles).
3. **Given** the equity data endpoint, **When** it is slow or errors, **Then** loading and error states are shown within the new design (not broken/raw).

---

### User Story 2 - Redesigned strategy browse & analysis (Priority: P2)

A user browses the multi-pair strategy grid, runs a backtest, and reads the
AI agent analysis, all within the same modern visual language. The Browse tab,
strategy cards, filters, sparklines, backtest runner, and agent-analysis cards
are restyled consistently with the dashboard.

**Why this priority**: This is the second major surface and where most interaction
happens. Consistency with US1 is what makes the redesign feel intentional.

**Independent Test**: Can be verified by opening the Browse tab and exercising
filters, a strategy card, a backtest run, and an agent-analysis card; all render
in the new style and retain their function.

**Acceptance Scenarios**:

1. **Given** the Browse tab, **When** the user applies a filter, **Then** the strategy grid updates and the filter controls match the new design.
2. **Given** a strategy card with a sparkline, **When** the user opens it, **Then** the backtest runner and agent-analysis card render in the new style and remain functional.
3. **Given** the new design, **When** the user switches between Dashboard and Browse tabs, **Then** the navigation/transition feels cohesive (shared theme, not two disjoint UIs).

---

### Edge Cases

- What happens when the equity endpoint returns no data yet (first run)? The new
  design must show an empty/loading state gracefully, not a broken layout.
- What happens on narrow/mobile widths? The new layout should remain usable
  (responsive), even if the primary target is desktop.
- How are the existing automated tests affected? The component tests
  (`Dashboard.test.tsx`, `BacktestRunner.test.tsx`, `browse.test.tsx`) must still
  pass; restyling must not break test selectors/structure where feasible.
- How is the current "retro-futurist terminal" aesthetic (charcoal/amber/emerald,
  grid overlay, DM Mono) reconciled? It is replaced by the Cryptix-inspired
  language unless the user prefers to keep accents (see clarification below).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The dashboard MUST preserve all currently displayed data: portfolio equity, realized/unrealized P&L, max drawdown, and the equity curve chart.
- **FR-002**: The Browse tab MUST preserve all current capabilities: multi-pair strategy grid, filters, per-strategy cards with sparklines, backtest runner, and AI agent-analysis cards.
- **FR-003**: The redesigned UI MUST apply a single, coherent visual language across both the Dashboard and Browse surfaces (shared theme tokens: color, radius, spacing, typography, shadows).
- **FR-004**: The redesign MUST be inspired by the Cryptix template's modern SaaS aesthetic (clean layout, rounded cards, soft shadows, strong typography, generous whitespace).
- **FR-005**: Loading, empty, and error states MUST be styled within the new design (no raw/broken fallbacks).
- **FR-006**: The redesign MUST remain responsive enough to be usable on common laptop and desktop widths, and degrade gracefully on narrow widths.
- **FR-007**: Existing automated component tests MUST continue to pass after restyling.
- **FR-008**: The new theme MUST be driven by centralized design tokens (CSS variables / theme constants) so future tweaks are single-point changes.

### Key Entities

- **Design tokens**: Centralized visual constants (colors, radii, spacing scale, font families, shadow levels) that define the Cryptix-inspired language.
- **Dashboard surface**: Portfolio summary (equity, P&L, drawdown) + equity curve.
- **Browse surface**: Strategy grid, filters, strategy detail (sparkline, backtest, agent analysis).
- **API contracts (unchanged)**: `/equity`, `/api/strategies`, `/api/backtest`, `/api/reflections`, `/api/stats` — the redesign consumes the same endpoints; no backend changes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of currently displayed portfolio and strategy data remains visible after the redesign (no information removed).
- **SC-002**: The Dashboard and Browse surfaces share one coherent theme (verified by a single source of design tokens with no duplicate/conflicting hard-coded values).
- **SC-003**: Existing automated UI tests pass after restyling (regression rate = 0 from the visual change).
- **SC-004**: A user can complete the primary journey (view portfolio → open Browse → run a backtest → read agent analysis) entirely within the new visual language.

## Assumptions

- The Cryptix template is used as a **visual/design-language reference** (modern Framer SaaS aesthetic), not as a drop-in HTML/CSS to copy verbatim. The crypto-bot frontend stays a React + TypeScript (Vite) SPA consuming the existing FastAPI endpoints.
- The Framer/reference site could not be fully inspected by automated fetch (only title metadata retrieved). Concrete visual tokens (exact hex palette, font names, section layout) are therefore inferred from the "modern SaaS website template" genre and the project's existing component inventory. Final tokens are adjustable.
- Backend/API is unchanged; this is a presentation-layer feature only.
- The existing "retro-futurist terminal" aesthetic is intentionally replaced. If the user wants to keep neon/terminal accents, that is captured as a clarification.
- Scope is **restyling/redesign of existing surfaces**, not adding new dashboard features (no new charts, no new data sources) unless separately requested.
- Tech stack retained: React 18 + TypeScript + Vite + Biome, served by the existing FastAPI app. GitFlow branch `feature/dashboard-cryptix-redesign` (separate from `feature/constitution-compliance`).

## Open Clarification (single, non-blocking)

**Retain terminal accents?** The current UI is a "retro-futurist terminal"
(charcoal/amber/emerald, grid overlay, monospace numbers). Cryptix is a cleaner
modern SaaS look. Default decision: **replace** the terminal aesthetic with the
Cryptix-inspired language (FR-004). If you want to **keep** neon/mono accents as a
hybrid, say so and I'll fold them into the tokens. This does not block the spec;
the default is applied and adjustable during planning/implementation.
