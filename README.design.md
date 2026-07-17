# Signal Terminal — Design System

Sistema de design do dashboard (`dashboard/`). Estética **quant signal terminal**:
monoespaçado pra dados, display em Syne, accents de sinal, grid + grain, molduras de
instrumento com cantos em colchete, reveal escalonado, hover glow.

Nada de Inter / Space-Grotesk / gradiente roxo (anti "AI slop").

## Princípios

1. **Dados em mono.** Tudo que é número, código ou label técnico usa `JetBrains Mono`.
2. **Display em Syne.** Títulos de página/seção (`h1`, `.browse-title`, `.report-title`,
   `.strat-card-name`) usam `Syne` 700–800, uppercase onde fizer sentido.
3. **Accents de sinal.** Cores semânticas, não decorativas:
   - `--sig-ok` `#3ddc97` — executar / positivo
   - `--sig-warn` `#ffb000` — revisar / alerta
   - `--sig-rej` `#ff4d6d` — rejeitar / negativo
   - `--accent` `#6ea8fe` (azul) — marca/UI primária, glow `--accent-glow`
4. **Moldura de instrumento.** Painéis com fundo `linear-gradient` leve + `1px` border +
   (opcional) cantos em colchete (`::before`/`::after` top-left/bottom-right).
5. **Medidores.** KPIs/células com `border-left: 2px solid accent`, label mono 9–10px,
   valor mono 16–18px bold.
6. **Atmosfera.** Grid de fundo (`--sig-grid`) + grain via `body::after`, cinza-escuro
   (`#0b0e14` / `#11151d`), contraste alto.
7. **Micro-interações.** Reveal `fadeSlideIn` escalonado nos cards; hover lift + glow;
   tab underline animado; botões mono com glow.

## Tokens (`:root` em `index.css`)

| Token | Valor | Uso |
|---|---|---|
| `--bg` | `#0b0e14` | fundo base |
| `--panel` | `#11151d` | painel |
| `--panel-2` | `#161b25` | superfície elevada / medidor |
| `--text` | `#e6edf3` | texto |
| `--muted` | `#7d8aa0` | label/secundário |
| `--border` | `#222a37` | borda |
| `--accent` | `#6ea8fe` | primário UI |
| `--accent-soft` | `rgba(110,168,254,.25)` | borda suave |
| `--accent-glow` | `rgba(110,168,254,.25)` | glow |
| `--sig-ok` | `#3ddc97` | sinal ok |
| `--sig-warn` | `#ffb000` | sinal warn |
| `--sig-rej` | `#ff4d6d` | sinal rej |
| `--sig-grid` | `rgba(110,168,254,.04)` | grid bg |
| `--green` / `--red` | `#22c55e` / `#ef4444` | PnL |
| `--font` | `'Syne'` | display |
| `--font-mono` | `'JetBrains Mono'` | dados |
| `--radius` | `14px` | raio padrão |

## Componentes cobertos

- **Header** (`Header.tsx`): moldura de instrumento, logo glow, sublinha accent animada,
  subtitle mono `PAPER TRADING · SPOT`.
- **Tabs** (`Dashboard.tsx`): underline animado, active Syne/mono glow.
- **StatCard** (`Dashboard.tsx`): moldura + corner tick, hover lift, reveal escalonado.
- **ScorePanel** (`ScorePanel.tsx`): gauge SVG composto, segment bars (12 células),
  stamp `EXECUTAR`/`REJEITAR`, reveal animado. Ver `ScorePanel.tsx` p/ detalhe.
- **Browse / StrategyCard**: cards com corner tick, chips `sym`/`tf`/`by` mono, sparkline
  em moldura inset.
- **FiltersBar**: labels mono, selects mono com focus glow.
- **BacktestRunner**: moldura com cantos, título Syne, KPIs medidores.
- **Report / Details / Trades**: molduras com cantos, kickers mono, tabela com hover glow.
- **AgentAnalysisCard / ReflectionPanel**: borda-esquerda accent, mono, cantos.
- **Botões** (`.btn-primary`/`.btn-secondary`): mono, glow accent.

## Fontes

Carregadas em `dashboard/index.html` (Google Fonts):
`Syne` (700, 800) + `JetBrains Mono` (400, 600, 700).

## Build

```bash
cd dashboard
npm install --include=dev
npm run build      # tsc -b && vite build -> dist/
```

Backend serve `dashboard/dist/` em `core/strategy_api.py` (`STATIC_DIR`).

## Testes

```bash
cd dashboard && npx vitest run
```

Cobrem `Dashboard`, `BacktestRunner` (7 testes). Estrutura visual validada por build +
serviço HTTP 200 + presença de classes no CSS bundle.
