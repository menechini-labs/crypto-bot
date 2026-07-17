"""FastAPI application for crypto-bot strategy API, browse, backtest, downloads, and agent analysis.

Unified server: serves API routes (/api/*), equity data (/equity),
and the React SPA frontend (dashboard/dist/) on a single port.
"""

from __future__ import annotations

import logging
import mimetypes
import os
import zipfile
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

try:
    import uvicorn
except ImportError:
    uvicorn = None  # type: ignore[assignment]

from core.agent_analyzer import analyze_backtest
from core.reflection import load_reflections as _load_reflections
from core.reflection import reflect_trades, save_reflection

logger = logging.getLogger("crypto-bot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app: FastAPI = FastAPI(
    title="Crypto Bot Strategy API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Estratégias mock
# ---------------------------------------------------------------------------

STRATEGIES_MOCK: list[dict[str, Any]] = [
    {
        "id": "grid_static_btc",
        "name": "Grid Static BTC",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "author": "Eduardo S.",
        "netProfitPct": 8.45,
        "profitFactor": 1.42,
        "maxDrawdownPct": 12.3,
        "winRatePct": 61.8,
        "sharpeRatio": 1.12,
        "sortinoRatio": 1.62,
        "totalTrades": 127,
        "equityCurve": [1.0, 1.02, 1.05, 1.03, 1.08, 1.06, 1.12, 1.15, 1.13, 1.18],
        "forkUrl": "/api/strategies/grid_static_btc/fork.json",
    },
    {
        "id": "grid_dynamic_eth",
        "name": "Grid Dynamic ETH",
        "symbol": "ETHUSDT",
        "timeframe": "4h",
        "author": "CryptoWhale",
        "netProfitPct": 15.2,
        "profitFactor": 1.87,
        "maxDrawdownPct": 8.9,
        "winRatePct": 68.5,
        "sharpeRatio": 1.45,
        "sortinoRatio": 2.12,
        "totalTrades": 89,
        "equityCurve": [1.0, 1.03, 1.07, 1.05, 1.12, 1.10, 1.18, 1.22, 1.20, 1.25],
        "forkUrl": "/api/strategies/grid_dynamic_eth/fork.json",
    },
    {
        "id": "trend_follow_sol",
        "name": "Trend Follow SOL",
        "symbol": "SOLUSDT",
        "timeframe": "1h",
        "author": "QuantBrasil",
        "netProfitPct": -5.2,
        "profitFactor": 0.89,
        "maxDrawdownPct": 28.7,
        "winRatePct": 42.3,
        "sharpeRatio": -0.34,
        "sortinoRatio": -0.48,
        "totalTrades": 156,
        "equityCurve": [1.0, 0.98, 0.95, 0.92, 0.90, 0.88, 0.85, 0.82, 0.80, 0.78],
        "forkUrl": "/api/strategies/trend_follow_sol/fork.json",
    },
]

_VALID_STRATEGIES = frozenset({"grid", "grid_dynamic", "combined", "baseline", "default"})
_VALID_REGIMES = frozenset({"lateral", "uptrend", "downtrend"})

# ---------------------------------------------------------------------------
# Endpoints: estratégias
# ---------------------------------------------------------------------------


@app.get("/api/strategies")
async def list_strategies(
    symbol: str | None = Query(None),
    timeframe: str | None = Query(None),
    minPnl: float | None = Query(None, ge=-100, le=1000),
    maxDd: float | None = Query(None, ge=0, le=100),
    minSharpe: float | None = Query(None),
    author: str | None = Query(None),
) -> JSONResponse:
    logger.info("list_strategies symbol=%s timeframe=%s", symbol, timeframe)
    results = STRATEGIES_MOCK
    if symbol:
        results = [s for s in results if s["symbol"] == symbol]
    if timeframe:
        results = [s for s in results if s["timeframe"] == timeframe]
    if minPnl is not None:
        results = [s for s in results if s["netProfitPct"] >= minPnl]
    if maxDd is not None:
        results = [s for s in results if s["maxDrawdownPct"] <= maxDd]
    if minSharpe is not None:
        results = [s for s in results if s["sharpeRatio"] >= minSharpe]
    if author:
        results = [s for s in results if s["author"] == author]
    return JSONResponse(results)


@app.get("/api/strategies/{strategy_id}")
async def get_strategy(strategy_id: str) -> dict[str, Any] | None:
    for s in STRATEGIES_MOCK:
        if s["id"] == strategy_id:
            return s
    return None


@app.get("/api/strategies/{strategy_id}/fork.json")
async def fork_strategy(strategy_id: str) -> dict[str, Any] | None:
    for s in STRATEGIES_MOCK:
        if s["id"] == strategy_id:
            return s
    return None


@app.get("/api/stats")
async def get_stats() -> dict[str, Any]:
    logger.info("get_stats")
    total = len(STRATEGIES_MOCK)
    avg_pnl = sum(s["netProfitPct"] for s in STRATEGIES_MOCK) / total if total else 0
    avg_sharpe = sum(s["sharpeRatio"] for s in STRATEGIES_MOCK) / total if total else 0
    return {
        "totalStrategies": total,
        "averagePnL": round(avg_pnl, 2),
        "averageSharpe": round(avg_sharpe, 2),
        "timestamp": datetime.now(UTC).isoformat(),
    }


# ---------------------------------------------------------------------------
# Cache de backtests + endpoints
# ---------------------------------------------------------------------------

_BACKTEST_CACHE: dict[str, dict[str, Any]] = {}


def _bt_id(symbol: str, strategy: str, regime: str, seed: int) -> str:
    return f"{symbol.replace('/', '_')}_{strategy}_{regime}_{seed}"


@app.post("/api/score")
async def api_score(payload: dict[str, Any]) -> dict[str, Any]:
    """Calcula o scoring de um sinal dado um histórico de closes.

    Body: {
      "closes": [float, ...],   # obrigatório (>= 20)
      "signal": "buy"|"sell"|"hold",
      "has_position": bool,
      "ctx": { ... }            # opcional (symbol, regime, volatility, sl_pct, tp_pct)
    }
    Retorna o SignalScore serializado (confiança, risco, composite, componentes).
    """
    logger.info("api_score signal=%s closes=%d", payload.get("signal"), len(payload.get("closes", [])))
    from core.scoring import score_signal, explain_score

    closes = payload.get("closes")
    if not isinstance(closes, list) or len(closes) < 20:
        raise HTTPException(422, "closes deve ser lista com >= 20 valores")
    signal = payload.get("signal", "hold")
    if signal not in ("buy", "sell", "hold"):
        raise HTTPException(422, "signal deve ser buy|sell|hold")
    has_position = bool(payload.get("has_position", False))
    ctx = payload.get("ctx") or {
        "symbol": "BTCUSDT",
        "regime": "lateral",
        "volatility": 2.5,
        "sl_pct": 5.0,
        "tp_pct": 10.0,
    }
    score = score_signal([float(c) for c in closes], signal, has_position, ctx)
    return {
        "status": "ok",
        "signal": signal,
        "score": score.__dict__,
        "explanation": explain_score(score),
    }


@app.post("/api/backtest")
async def api_backtest(payload: dict[str, Any]) -> dict[str, Any]:
    """Roda backtest, cacheia, retorna report + analysis."""
    logger.info(
        "api_backtest symbol=%s strategy=%s regime=%s n=%d seed=%d",
        payload.get("symbol"),
        payload.get("strategy"),
        payload.get("regime"),
        payload.get("n", 300),
        payload.get("seed", 42),
    )
    from core.backtest import run_backtest as _run
    from core.config_loader import load_config
    from core.synth import make_series

    regime = payload.get("regime", "lateral")
    strategy_name = payload.get("strategy", "grid")
    symbol = payload.get("symbol", "BTCUSDT")
    n = int(payload.get("n", 300))
    seed = int(payload.get("seed", 42))

    if strategy_name not in _VALID_STRATEGIES:
        raise HTTPException(422, f"strategia invalida: {strategy_name}")
    if regime not in _VALID_REGIMES:
        raise HTTPException(422, f"regime invalido: {regime}")
    if n < 50 or n > 2000:
        raise HTTPException(422, "n deve estar entre 50 e 2000")

    cfg = load_config()
    closes = make_series(regime=regime, n=n, seed=seed)
    use_scoring = bool(payload.get("use_scoring", True))
    raw = _run(closes, cfg, symbol=symbol, strategy_name=strategy_name, use_scoring=use_scoring)
    raw["regime"] = regime
    raw["seed"] = seed

    step = max(1, n // 60)
    bt_id = _bt_id(symbol, strategy_name, regime, seed)
    report: dict[str, Any] = {
        "id": bt_id,
        "symbol": symbol,
        "strategy": strategy_name,
        "regime": regime,
        "timeframe": "1h",
        "candles": n,
        "seed": seed,
        "equity": raw.get("equity", cfg.get("initial_cash_usdt", 1000.0)),
        "final_equity": raw.get("final_equity", 0.0),
        "pnl": raw.get("pnl", 0.0),
        "pnl_pct": round(raw.get("pnl_pct", 0.0), 4),
        "max_drawdown_pct": round(raw.get("max_drawdown_pct", 0.0), 4),
        "win_rate": round(raw.get("win_rate", 0.0), 4),
        "sharpe": round(raw.get("sharpe", 0.0), 4),
        "cagr": round(raw.get("cagr", 0.0), 4),
        "trades": raw.get("trades", 0),
        "profit_factor": raw.get("profit_factor"),
        "sortino": raw.get("sortino"),
        "calmar": raw.get("calmar"),
        "equity_curve": closes[::step],
        "trades_list": raw.get("trades_list", []),
        "timestamp": datetime.now(UTC).isoformat(),
        "source": "local",
    }

    _BACKTEST_CACHE[bt_id] = report
    analysis = analyze_backtest(report).to_dict()

    return {"status": "ok", "report": report, "analysis": analysis}


@app.get("/api/backtest/{bt_id}")
async def get_backtest(bt_id: str) -> dict[str, Any]:
    """Retorna relatório + analysis de backtest cacheado."""
    logger.info("get_backtest id=%s", bt_id)
    report = _BACKTEST_CACHE.get(bt_id)
    if not report:
        raise HTTPException(404, f"Backtest {bt_id} nao encontrado")
    analysis = analyze_backtest(report).to_dict()
    return {"status": "ok", "report": report, "analysis": analysis}


@app.post("/api/backtest/{bt_id}/reflection")
async def backtest_reflection(bt_id: str) -> dict[str, Any]:
    """Gera reflexão pros trades de um backtest cacheado."""
    logger.info("backtest_reflection id=%s", bt_id)
    report = _BACKTEST_CACHE.get(bt_id)
    if not report:
        raise HTTPException(404, f"Backtest {bt_id} nao encontrado")
    trades = report.get("trades_list", [])
    if not trades:
        return {
            "status": "ok",
            "reflection": {"total_trades": 0, "insights": ["Nenhum trade registrado"]},
        }
    reflection = reflect_trades(
        trades,
        regime=report.get("regime", "unknown"),
        strategy=report.get("strategy", "unknown"),
        symbol=report.get("symbol", "unknown"),
    )
    save_reflection(reflection)
    return {"status": "ok", "reflection": reflection}


@app.get("/api/reflections")
async def get_reflections(limit: int = Query(10, ge=1, le=50)) -> dict[str, Any]:
    """Retorna historico de reflexoes salvas."""
    return {"status": "ok", "reflections": _load_reflections(limit=limit)}


# ---------------------------------------------------------------------------
# Endpoint: download do projeto (.zip)
# ---------------------------------------------------------------------------


@app.get("/download/project")
async def download_project() -> FileResponse:
    logger.info("download_project")
    tmp_zip = "/tmp/crypto-bot-project.zip"
    if os.path.exists(tmp_zip):
        os.remove(tmp_zip)

    root = os.getcwd()
    with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, _dirnames, filenames in os.walk(root):
            if "node_modules" in dirpath or ".venv" in dirpath or "__pycache__" in dirpath:
                continue
            for f in filenames:
                fp = os.path.join(dirpath, f)
                arcname = os.path.relpath(fp, root)
                z.write(fp, arcname)

    return FileResponse(
        tmp_zip, media_type="application/zip", filename="crypto-bot-project.zip"
    )


# ---------------------------------------------------------------------------
# Static files + SPA frontend (dashboard/dist/)
# ---------------------------------------------------------------------------

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(ROOT_DIR, "dashboard", "dist")
EQUITY_PATH = os.path.join(ROOT_DIR, "data", "equity.json")


@app.get("/equity")
async def get_equity() -> Response:
    if os.path.exists(EQUITY_PATH):
        with open(EQUITY_PATH, encoding="utf-8") as f:
            data = f.read()
    else:
        data = "[]"
    return Response(content=data, media_type="application/json")


@app.get("/", response_model=None)
async def serve_index():
    fpath = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(fpath):
        return FileResponse(fpath, media_type="text/html")
    return Response(status_code=404, content="Dashboard nao compilado. Rode `npm run build` em dashboard/")


@app.get("/{full_path:path}", response_model=None)
async def spa_fallback(full_path: str):
    # Deixa FastAPI lidar com /docs, /openapi.json (registrados internamente)
    # /api/* routes sao definidas acima e tomam prioridade
    if full_path.startswith("api/"):
        return Response(status_code=404)

    # Tenta servir como arquivo estatico real
    fpath = os.path.join(STATIC_DIR, full_path)
    if os.path.exists(fpath) and os.path.isfile(fpath):
        ctype, _ = mimetypes.guess_type(fpath)
        return FileResponse(fpath, media_type=ctype or "application/octet-stream")

    # SPA fallback: toda rota nao-API serve index.html (para React Router)
    spa_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(spa_path):
        return FileResponse(spa_path, media_type="text/html")

    return Response(status_code=404, content="Not found")


# ---------------------------------------------------------------------------
# Factory & entrypoint
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    return app


if __name__ == "__main__":
    if uvicorn is None:
        print("Instale dependencias: pip install uvicorn")
        raise SystemExit(1)
    uvicorn.run(app, host="0.0.0.0", port=8000)
