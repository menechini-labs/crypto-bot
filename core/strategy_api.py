"""FastAPI application for crypto-bot strategy API, browse, backtest, downloads, and agent analysis.

Unified server: serves API routes (/api/*), equity data (/equity),
and the React SPA frontend (dashboard/dist/) on a single port.
"""

from __future__ import annotations

import logging
import mimetypes
import os
import json
import time
import threading
import zipfile
from datetime import UTC, datetime
from pathlib import Path


def _load_dotenv() -> None:
    """Minimal .env loader (stdlib only). Sets os.environ from .env if present."""
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except Exception:
        pass


_load_dotenv()
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
from core.strategy_registry.registry import get_all as _registry_get_all
from core import market as _market
from core import indicators as _ind
from core import agent_desk as _agent_desk
from core import news as _news
from core import paper_engine as _paper_engine
from core.scoring import score_signal as _score_signal, detect_regime as _detect_regime, should_execute
from core.external_sources import EXTERNAL_SOURCES

logger = logging.getLogger("crypto-bot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ---------------------------------------------------------------------------
# Observability counters (Phase 0)
# ---------------------------------------------------------------------------

_METRICS: dict[str, int] = {
    "signals_scored": 0,
    "llm_calls": 0,
    "llm_errors": 0,
    "backtests_run": 0,
    "orders_paper": 0,
    "risk_rejections": 0,
}

# In-memory caches (Phase 0/1)
_KLINES_CACHE: dict[str, tuple[float, list[float]]] = {}
_KLINES_TTL = 5.0
_INDICES_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_INDICES_TTL = 60.0

# Cache de backtest pré-populado (Phase 4+)
# Preenchido no startup: mapeia id-da-estrategia -> dict de métricas
_BACKTEST_CACHE: dict[str, dict[str, Any]] = {}


def _cached_closes(symbol: str, tf: str, limit: int) -> list[float]:
    """Fetch closes from Binance public klines with short TTL cache."""
    import time
    key = f"{symbol}|{tf}|{limit}"
    now = time.time()
    cached = _KLINES_CACHE.get(key)
    if cached and now - cached[0] < _KLINES_TTL:
        return cached[1]
    candles = _market.fetch_ohlcv(symbol, tf, limit)
    closes = [float(c["close"]) for c in candles]
    _KLINES_CACHE[key] = (now, closes)
    return closes

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
# Startup: prime backtest cache
# ---------------------------------------------------------------------------

async def _warm_backtest_cache() -> None:
    """Roda backtest leve para todas as estratégias conhecidas.
    Preenche _BACKTEST_CACHE com resultados reais.
    Falha silenciosa se mercado offline.
    """
    try:
        closes = _cached_closes("BTCUSDT", "1h", 200)
    except Exception:
        logger.warning("warm_backtest: sem dados de mercado, pulando")
        return
    if len(closes) < 50:
        return

    from core.config_loader import load_config as _load_cfg
    cfg = _load_cfg("config.yaml")
    config = {
        "initial_cash_usdt": cfg.get("initial_cash_usdt", 10000.0),
        "fee_pct": cfg.get("fee_pct", 0.001),
        "max_position_pct": cfg.get("max_position_pct", 0.5),
        "stop_loss_pct": cfg.get("stop_loss_pct", 0.05),
        "take_profit_pct": cfg.get("take_profit_pct", 0.10),
    }

    from core.backtest import run_backtest as _run
    reg = _registry_get_all()
    for name in reg:
        # LLM strategy e avaliada ao vivo; warm_backtest por candle e lento
        # (cada decide() faz uma chamada de rede). Pula no cache de startup.
        if name == "llm":
            logger.info("warm_backtest %s pulado (avaliado ao vivo)", name)
            continue
        try:
            result = _run(closes, config, symbol="BTCUSDT", strategy_name=name, use_scoring=(name == "llm"))
            _BACKTEST_CACHE[name] = {
                "net_profit_pct": result.get("pnl", 0.0),
                "profit_factor": result.get("profit_factor"),
                "max_drawdown_pct": result.get("max_drawdown_pct", 0.0),
                "win_rate_pct": result.get("win_rate", 0.0),
                "sharpe": result.get("sharpe"),
                "sortino": result.get("sortino"),
                "total_trades": result.get("total_trades", 0),
                "equity_curve": result.get("equity_curve", []),
            }
            logger.info("warm_backtest %s OK pnl=%.2f%%", name, result.get("pnl", 0.0))
        except Exception as e:
            logger.warning("warm_backtest %s falhou: %s", name, e)


@app.on_event("startup")
async def _startup_warm_cache():
    await _warm_backtest_cache()

# ---------------------------------------------------------------------------
# Estratégias — derivadas do registry real (Phase 0: sem PnL fake)
# ---------------------------------------------------------------------------

def _build_strategies_from_registry() -> list[dict[str, Any]]:
    """Constrói metadados de estratégias a partir do registry real.

    Sem números de PnL inventados: hasBacktest=false até rodar backtest.
    """
    reg = _registry_get_all()
    out: list[dict[str, Any]] = []
    for name in sorted(reg.keys()):
        cached = _BACKTEST_CACHE.get(name, {})
        has_bt = bool(cached)
        out.append({
            "id": name,
            "name": name.replace("_", " ").title(),
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "author": "core",
            "netProfitPct": cached.get("net_profit_pct") if has_bt else None,
            "profitFactor": cached.get("profit_factor") if has_bt else None,
            "maxDrawdownPct": cached.get("max_drawdown_pct") if has_bt else None,
            "winRatePct": cached.get("win_rate_pct") if has_bt else None,
            "sharpeRatio": cached.get("sharpe") if has_bt else None,
            "sortinoRatio": cached.get("sortino") if has_bt else None,
            "totalTrades": cached.get("total_trades") if has_bt else None,
            "equityCurve": cached.get("equity_curve", []) if has_bt else [],
            "forkUrl": "",
            "hasBacktest": has_bt,
        })
    return out

_VALID_STRATEGIES = frozenset({"grid", "grid_dynamic", "combined", "baseline", "default", "llm",
                            "ma_cross", "rsi_oversold", "bollinger_reversal", "trend_follow", "macd_signal"})
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
    results = _build_strategies_from_registry()
    if symbol:
        results = [s for s in results if s["symbol"] == symbol]
    if timeframe:
        results = [s for s in results if s["timeframe"] == timeframe]
    if minPnl is not None:
        results = [s for s in results if s["netProfitPct"] is not None and s["netProfitPct"] >= minPnl]
    if maxDd is not None:
        results = [s for s in results if s["maxDrawdownPct"] is not None and s["maxDrawdownPct"] <= maxDd]
    if minSharpe is not None:
        results = [s for s in results if s["sharpeRatio"] is not None and s["sharpeRatio"] >= minSharpe]
    if author:
        results = [s for s in results if s["author"] == author]
    return JSONResponse(results)


@app.get("/api/strategies/{strategy_id}")
async def get_strategy(strategy_id: str) -> dict[str, Any] | None:
    for s in _build_strategies_from_registry():
        if s["id"] == strategy_id:
            return s
    return None


@app.get("/api/stats")
async def get_stats() -> dict[str, Any]:
    logger.info("get_stats")
    reg = _build_strategies_from_registry()
    total = len(reg)
    return {
        "totalStrategies": total,
        "averagePnL": None,
        "averageSharpe": None,
        "timestamp": datetime.now(UTC).isoformat(),
    }


# ---------------------------------------------------------------------------
# Cache de backtests + endpoints
# ---------------------------------------------------------------------------

_BACKTEST_CACHE: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Mode state: DEMO (observation only) vs REAL (paper execution enabled)
# ---------------------------------------------------------------------------
# DEMO: no order execution. REAL: PaperEngine execution allowed.
# REAL requires ALLOW_LIVE_TRADING=1 at process level to take effect.
_ALLOW_LIVE = os.getenv("ALLOW_LIVE_TRADING") == "1"
_MODE: str = (os.getenv("MODE") or "demo").lower()
if _MODE not in ("demo", "real"):
    _MODE = "demo"


def _mode_is_real() -> bool:
    """REAL active only if MODE=real AND ALLOW_LIVE_TRADING=1."""
    return _MODE == "real" and _ALLOW_LIVE


def _set_mode(new_mode: str) -> bool:
    """Set runtime mode. Returns True if applied."""
    global _MODE
    new_mode = (new_mode or "").lower()
    if new_mode not in ("demo", "real"):
        return False
    if new_mode == "real" and not _ALLOW_LIVE:
        return False
    _MODE = new_mode
    return True


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


@app.post("/api/llm-signal")
async def api_llm_signal(payload: dict[str, Any]) -> dict[str, Any]:
    """Roda LLMStrategy.decide sobre um histórico e retorna sinal + score.

    Body: { "closes": [float,...] (>=20), "has_position": bool, "ctx": {...} }
    Requer ENABLE_LLM=1 e LLM_API_KEY; sem isso retorna fallback 'hold' com aviso.
    """
    logger.info("api_llm_signal closes=%d", len(payload.get("closes", [])))
    from core.scoring import score_signal, explain_score
    from core.strategy_registry.llm_strategy import LLMStrategy, _is_enabled

    closes = payload.get("closes")
    if not isinstance(closes, list) or len(closes) < 20:
        raise HTTPException(422, "closes deve ser lista com >= 20 valores")
    has_position = bool(payload.get("has_position", False))
    ctx = payload.get("ctx") or {
        "symbol": "BTCUSDT",
        "regime": "lateral",
        "volatility": 2.5,
        "sl_pct": 5.0,
        "tp_pct": 10.0,
    }
    strat = LLMStrategy()
    signal = strat.decide([float(c) for c in closes], has_position, ctx=ctx)
    enabled = _is_enabled()
    score = score_signal([float(c) for c in closes], signal, has_position, ctx)
    return {
        "status": "ok",
        "llm_enabled": enabled,
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
    _strategy_obj = None
    if strategy_name == "llm":
        from core.strategy_registry.llm_strategy import LLMStrategy
        _strategy_obj = LLMStrategy()
    raw = _run(
        closes,
        cfg,
        symbol=symbol,
        strategy_name=strategy_name if _strategy_obj is None else "llm",
        use_scoring=use_scoring,
        strategy=_strategy_obj,
    )
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
# Phase 0/1: observability, market data, indicators, indices, signals
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health() -> dict[str, Any]:
    """Health check: backend vivo + componentes disponíveis."""
    import importlib.util
    llm_enabled = bool(os.getenv("ENABLE_LLM")) and bool(os.getenv("LLM_API_KEY"))
    return {
        "status": "ok",
        "time": datetime.now(UTC).isoformat(),
        "version": app.version,
        "mode": _MODE,
        "mode_real": _mode_is_real(),
        "allow_live_trading": _ALLOW_LIVE,
        "llm_enabled": llm_enabled,
        "registry_strategies": sorted(_registry_get_all().keys()),
        "scoring_available": importlib.util.find_spec("core.scoring") is not None,
        "indicators_available": importlib.util.find_spec("core.indicators") is not None,
    }


@app.get("/api/mode")
async def get_mode() -> dict[str, Any]:
    """Current mode + whether REAL execution is possible."""
    return {
        "mode": _MODE,
        "real_available": _ALLOW_LIVE,
        "real_active": _mode_is_real(),
    }

@app.post("/api/mode")
async def set_mode(payload: dict[str, Any]) -> dict[str, Any]:
    """Switch mode. REAL requires ALLOW_LIVE_TRADING=1; rejected otherwise."""
    new_mode = str(payload.get("mode", "")).lower()
    if new_mode not in ("demo", "real"):
        raise HTTPException(status_code=400, detail="mode deve ser 'demo' ou 'real'")
    if new_mode == "real" and not _ALLOW_LIVE:
        raise HTTPException(
            status_code=403,
            detail="REAL mode bloqueado: defina ALLOW_LIVE_TRADING=1 no ambiente",
        )
    if not _set_mode(new_mode):
        raise HTTPException(status_code=400, detail="falha ao aplicar modo")
    logger.info("mode alterado para %s", _MODE)
    _persist_mode(_MODE)
    return {"mode": _MODE, "real_active": _mode_is_real()}


def _persist_mode(mode: str) -> None:
    """Write MODE to .env if present (persists restart)."""
    try:
        root = Path(__file__).resolve().parent.parent
        env_path = root / ".env"
        if not env_path.exists():
            return
        lines = env_path.read_text(encoding="utf-8").splitlines()
        out = []
        replaced = False
        for ln in lines:
            if ln.strip().startswith("MODE="):
                out.append(f"MODE={mode}")
                replaced = True
            else:
                out.append(ln)
        if not replaced:
            out.append(f"MODE={mode}")
        env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    except Exception:
        pass


@app.get("/api/swarm-presets")
async def api_swarm_presets() -> list[dict]:
    """Retorna lista de presets de time multi-agent (swarm)."""
    from core.swarm_presets import list_presets
    return list_presets()


@app.get("/api/external")
async def external() -> dict[str, str]:
    """URLs externas de referência (mcp-api TraderDev)."""
    return dict(EXTERNAL_SOURCES)


@app.get("/api/metrics")
async def metrics() -> dict[str, Any]:
    """Contadores de observabilidade (Prometheus-friendly em JSON)."""
    return {"status": "ok", "metrics": dict(_METRICS), "ts": datetime.now(UTC).isoformat()}


@app.get("/api/risk/state")
async def risk_state() -> dict[str, Any]:
    """Estado do risk guard em run-time (thresholds de SL/TP, trailing, etc)."""
    from core import config_loader
    cfg = config_loader.load_config()
    risk = cfg.get("risk", {}) if isinstance(cfg, dict) else {}
    return {
        "status": "ok",
        "config": {
            "max_position_pct": risk.get("max_position_pct", 0.1),
            "stop_loss_pct": risk.get("stop_loss_pct", 0.05),
            "take_profit_pct": risk.get("take_profit_pct", 0.1),
            "max_drawdown_pct": risk.get("max_drawdown_pct", 0.2),
            "trailing_stop_pct": risk.get("trailing_stop_pct", 0.0),
            "daily_loss_limit_pct": risk.get("daily_loss_limit_pct", 0.1),
        },
        "metrics": {
            "risk_rejections": _METRICS["risk_rejections"],
            "orders_paper": _METRICS["orders_paper"],
        },
        "paper_only": True,
    }


@app.get("/api/market/closes")
async def market_closes(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    limit: int = Query(100, ge=20, le=1000),
) -> dict[str, Any]:
    """Fechamentos reais da Binance (público, sem auth). TTL cache 5s."""
    try:
        closes = _cached_closes(symbol, timeframe, limit)
    except Exception as exc:  # noqa: BLE001
        logger.warning("market_closes falhou: %s", exc)
        raise HTTPException(502, f"Falha ao buscar klines: {exc}")
    return {
        "status": "ok",
        "symbol": symbol,
        "timeframe": timeframe,
        "count": len(closes),
        "closes": closes,
    }


@app.get("/api/market/overview")
async def market_overview(
    symbols: str = Query("BTCUSDT,ETHUSDT,SOLUSDT"),
    timeframe: str = Query("1h"),
    limit: int = Query(50, ge=20, le=500),
) -> dict[str, Any]:
    """Visão geral de múltiplos símbolos: último preço, variação % e regime."""
    out: list[dict[str, Any]] = []
    for sym in [s.strip().upper() for s in symbols.split(",") if s.strip()]:
        try:
            closes = _cached_closes(sym, timeframe, limit)
            if len(closes) < 2:
                continue
            last = closes[-1]
            prev = closes[0]
            change_pct = ((last - prev) / prev) * 100 if prev else 0.0
            regime = _detect_regime(closes[-30:]) if len(closes) >= 30 else "lateral"
            out.append({
                "symbol": sym,
                "last": last,
                "change_pct": round(change_pct, 2),
                "regime": regime,
                "count": len(closes),
            })
        except Exception as exc:  # noqa: BLE001
            logger.warning("market_overview %s falhou: %s", sym, exc)
            out.append({"symbol": sym, "error": str(exc)})
    return {"status": "ok", "timeframe": timeframe, "markets": out}


@app.post("/api/indicators")
async def api_indicators(payload: dict[str, Any]) -> dict[str, Any]:
    """Calcula indicadores técnicos reutilizando core.indicators.

    Body: {"closes": [float,...], "symbol": str?, "timeframe": str?}
    """
    closes = payload.get("closes")
    if not isinstance(closes, list) or len(closes) < 30:
        raise HTTPException(422, "closes deve ser lista com >= 30 valores")
    c = [float(x) for x in closes]
    try:
        rsi = _ind.rsi(c)
        macd = _ind.macd(c)
        bb = _ind.bollinger(c)
        cross = _ind.ma_cross(c)
        sma20 = _ind.sma(c, 20)
        ema50 = _ind.ema(c, 50)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Erro ao calcular indicadores: {exc}")
    return {
        "status": "ok",
        "symbol": payload.get("symbol", "BTCUSDT"),
        "timeframe": payload.get("timeframe", "1h"),
        "rsi": rsi,
        "macd": macd,
        "bollinger": {"mid": bb[0], "upper": bb[1], "lower": bb[2]},
        "ma_cross": cross,
        "sma20": sma20,
        "ema50": ema50,
    }


@app.get("/api/indices")
async def api_indices() -> dict[str, Any]:
    """Índices de mercado gratuitos e sem auth: medo/ganância + top moedas.

    - alternative.me: Crypto Fear & Greed Index
    - CoinGecko: top moedas por market cap (grátis, sem chave)
    """
    import time
    now = time.time()
    cached = _INDICES_CACHE.get("indices")
    if cached and now - cached[0] < _INDICES_TTL:
        return {"status": "ok", "cached": True, **cached[1]}

    result: dict[str, Any] = {"fear_greed": None, "top_coins": [], "sources": []}
    # Fear & Greed (alternative.me)
    try:
        with _market._urlopen("https://api.alternative.me/fng/?limit=1") as resp:
            data = json.loads(resp.read().decode("utf-8"))
        fg = data.get("data", [{}])[0]
        result["fear_greed"] = {
            "value": int(fg.get("value", 0)),
            "classification": fg.get("value_classification", ""),
        }
        result["sources"].append("alternative.me")
    except Exception as exc:  # noqa: BLE001
        logger.warning("fear_greed falhou: %s", exc)
    # Top coins (CoinGecko)
    try:
        url = (
            "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd"
            "&order=market_cap_desc&per_page=10&page=1&sparkline=false"
        )
        with _market._urlopen(url) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        coins = []
        for row in data[:10]:
            coins.append({
                "id": row.get("id"),
                "symbol": (row.get("symbol") or "").upper(),
                "name": row.get("name"),
                "price": row.get("current_price"),
                "change_24h_pct": row.get("price_change_percentage_24h"),
                "market_cap": row.get("market_cap"),
            })
        result["top_coins"] = coins
        result["sources"].append("coingecko")
    except Exception as exc:  # noqa: BLE001
        logger.warning("coingecko falhou: %s", exc)
    _INDICES_CACHE["indices"] = (now, result)
    return {"status": "ok", "cached": False, **result}


@app.post("/api/signals")
async def api_signals(payload: dict[str, Any]) -> dict[str, Any]:
    """Gera sinais de scoring em lote a partir de closes reais (Binance).

    Body opcional: {"symbol", "timeframe", "limit", "regime"}
    Se 'closes' fornecido, usa-os; senão busca da Binance.
    """
    closes = payload.get("closes")
    symbol = payload.get("symbol", "BTCUSDT")
    timeframe = payload.get("timeframe", "1h")
    limit = int(payload.get("limit", 100))
    if not isinstance(closes, list) or len(closes) < 30:
        try:
            closes = _cached_closes(symbol, timeframe, limit)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(502, f"Falha ao buscar closes: {exc}")
    c = [float(x) for x in closes]
    from core.scoring import calculate_volatility
    regime = payload.get("regime") or (_detect_regime(c[-30:]) if len(c) >= 30 else "lateral")
    ctx = {
        "symbol": symbol,
        "regime": regime,
        "volatility": calculate_volatility(c),
        "sl_pct": 5.0,
        "tp_pct": 10.0,
    }
    signals = []
    for sig in ("buy", "sell", "hold"):
        score = _score_signal(c, sig, False, ctx)
        signals.append({
            "signal": sig,
            "composite": round(score.composite, 4),
            "confidence": round(score.confidence, 4),
            "risk": round(score.risk_score, 4),
            "execute": bool(should_execute(score)),
            "components": score.details.get("components", {}),
        })
    _METRICS["signals_scored"] += 1
    return {
        "status": "ok",
        "symbol": symbol,
        "timeframe": timeframe,
        "regime": regime,
        "count": len(c),
        "signals": signals,
    }


# ---------------------------------------------------------------------------
# Endpoint: Agent Desk cycle (Phase 2)
# ---------------------------------------------------------------------------

@app.get("/api/agents/cycle")
async def api_agents_cycle(team: str | None = None) -> dict[str, Any]:
    """Run a full Agent Desk cycle (Metrics/News/Risk/Strategy/DecisionCore).

    Se `team` for informado, filtra os agentes ao preset correspondente.
    """
    closes = _cached_closes("BTCUSDT", "1h", 100)
    if team:
        from core.swarm_presets import get_preset
        preset = get_preset(team)
        if preset:
            return _agent_desk.run_team(preset, closes if len(closes) >= 20 else None)
    cycle = _agent_desk.run_cycle(closes if len(closes) >= 20 else None)
    return cycle


_AGENT_EXEC_HISTORY: list[dict] = []


@app.post("/api/agents/execute")
async def api_agents_execute(payload: dict[str, Any]) -> dict[str, Any]:
    """Submit the Agent Desk decision as a paper order via PaperEngine.

    Body: {"cycle_id": int, "symbol": str (default BTCUSDT), "team": str | None}
    DEMO mode returns 403. REAL requires ALLOW_LIVE_TRADING=1.
    """
    if not _mode_is_real():
        raise HTTPException(403, "execucao desligada no modo DEMO")
    cycle_id = payload.get("cycle_id")
    symbol = payload.get("symbol", "BTCUSDT")
    team = payload.get("team")

    # Idempotency: same cycle_id already executed?
    for h in _AGENT_EXEC_HISTORY:
        if h.get("cycle_id") == cycle_id:
            return {"ok": False, "error": "cycle_id ja executado", "history": h}

    closes = _cached_closes(symbol, "1h", 100)
    if team:
        from core.swarm_presets import get_preset
        preset = get_preset(team)
        if preset:
            cycle = _agent_desk.run_team(preset, closes if len(closes) >= 20 else None)
            cycle["team"] = team
        else:
            cycle = _agent_desk.run_cycle(closes if len(closes) >= 20 else None)
    else:
        cycle = _agent_desk.run_cycle(closes if len(closes) >= 20 else None)

    decision = cycle.get("decision")
    if not decision:
        return {"ok": False, "error": "time sem DecisionCore — apenas analise"}
    verdict = decision.get("verdict")
    conf = decision.get("confidence", 0.0)
    if verdict not in ("buy", "sell") or conf < 0.5:
        return {"ok": False, "error": f"decisao {verdict} ignorada (conf={conf:.2f})"}

    from core import paper_engine as _paper
    engine = _paper.get_engine()
    snap = engine.snapshot()
    available = snap.get("available_cash") or snap.get("cash", 0.0)
    qty = _agent_desk._compute_qty(symbol, conf, available)
    if qty <= 0:
        return {"ok": False, "error": "qty <= 0 (sem caixa ou preco?)"}
    order = _paper.Order(
        symbol=symbol, side=verdict, qty=qty,
        sl_pct=0.02, tp_pct=0.05, trailing_pct=0.01,
        reason=f"AgentDesk {verdict} (conf {conf:.2f})",
        advisory=decision.get("reasoning", ""),
    )
    result = engine.submit(order)
    entry = {
        "cycle_id": cycle_id,
        "symbol": symbol,
        "verdict": verdict,
        "confidence": conf,
        "order_id": result.get("order", {}).get("id"),
        "qty": qty,
        "result": result,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "team": team,
    }
    _AGENT_EXEC_HISTORY.append(entry)
    return {"ok": bool(result.get("ok")), "execution": entry, "cycle": cycle}


@app.get("/api/agents/history")
async def api_agents_history() -> dict[str, Any]:
    """List of agent-triggered order executions (cycle_id -> order_id -> fill)."""
    return {"status": "ok", "count": len(_AGENT_EXEC_HISTORY), "history": _AGENT_EXEC_HISTORY}

# ---------------------------------------------------------------------------
# Agent Desk continuous loop control (PLAY / STOP)
# ---------------------------------------------------------------------------

_AGENT_LOOP_THREAD: threading.Thread | None = None
_AGENT_LOOP_STOP = threading.Event()
_AGENT_LOOP_INTERVAL = 20
_AGENT_LOOP_TEAM = "balanced"


def _agent_loop_worker() -> None:
    """Background worker: runs agent_desk cycles until stop event."""
    try:
        from core import agent_desk as _ad
        from core.market import fetch_ohlcv
        from core import paper_engine as _pe
        while not _AGENT_LOOP_STOP.is_set():
            try:
                symbol = _AGENT_LOOP_TEAM_SYMBOL if _AGENT_LOOP_TEAM_SYMBOL else "BTCUSDT"
                candles = fetch_ohlcv(symbol, "1h", 100)
                closes = [c["close"] for c in candles]
                cycle = _ad.run_cycle(closes if len(closes) >= 20 else None)
                decision = cycle["decision"]
                verdict, conf = decision["verdict"], decision["confidence"]
                if verdict in ("buy", "sell") and conf >= 0.5:
                    engine = _pe.get_engine()
                    snap = engine.snapshot()
                    avail = snap.get("available_cash", snap.get("cash", 0.0))
                    qty = _ad._compute_qty(symbol, conf, avail)
                    if qty > 0:
                        order = _pe.Order(
                            symbol=symbol, side=verdict, qty=qty,
                            sl_pct=0.02, tp_pct=0.05, trailing_pct=0.01,
                            reason=f"AgentDesk {verdict} (conf {conf:.2f})",
                            advisory=decision.get("reasoning", ""),
                        )
                        res = engine.submit(order)
                        logging.info("agent_loop %s %s -> ok=%s", verdict, qty, res.get("ok"))
            except Exception as e:
                logging.warning("agent_loop error: %s", e)
            _AGENT_LOOP_STOP.wait(_AGENT_LOOP_INTERVAL)
    except Exception as e:
        logging.error("agent_loop worker died: %s", e)


_AGENT_LOOP_TEAM_SYMBOL = "BTCUSDT"


@app.post("/api/agents/loop/start")
async def api_agents_loop_start(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """PLAY: start continuous agent desk loop (REAL mode only)."""
    global _AGENT_LOOP_THREAD, _AGENT_LOOP_TEAM, _AGENT_LOOP_TEAM_SYMBOL
    if _MODE != "real" or not _ALLOW_LIVE:
        raise HTTPException(status_code=403, detail="loop requer modo REAL + ALLOW_LIVE_TRADING=1")
    if _AGENT_LOOP_THREAD and _AGENT_LOOP_THREAD.is_alive():
        return {"status": "already_running", "running": True}
    _AGENT_LOOP_STOP.clear()
    _AGENT_LOOP_TEAM = (payload or {}).get("team", "balanced")
    _AGENT_LOOP_TEAM_SYMBOL = (payload or {}).get("symbol", "BTCUSDT")
    if (payload or {}).get("interval"):
        try:
            _AGENT_LOOP_INTERVAL = max(5, int((payload or {}).get("interval")))
        except (TypeError, ValueError):
            pass
    _AGENT_LOOP_THREAD = threading.Thread(target=_agent_loop_worker, daemon=True)
    _AGENT_LOOP_THREAD.start()
    return {"status": "started", "running": True, "team": _AGENT_LOOP_TEAM, "symbol": _AGENT_LOOP_TEAM_SYMBOL}


@app.post("/api/agents/loop/stop")
async def api_agents_loop_stop() -> dict[str, Any]:
    """STOP: halt continuous agent desk loop."""
    global _AGENT_LOOP_THREAD
    if not (_AGENT_LOOP_THREAD and _AGENT_LOOP_THREAD.is_alive()):
        return {"status": "not_running", "running": False}
    _AGENT_LOOP_STOP.set()
    _AGENT_LOOP_THREAD = None
    return {"status": "stopped", "running": False}


@app.get("/api/agents/loop/status")
async def api_agents_loop_status() -> dict[str, Any]:
    """Current loop state for UI."""
    running = bool(_AGENT_LOOP_THREAD and _AGENT_LOOP_THREAD.is_alive())
    return {
        "status": "ok",
        "running": running,
        "team": _AGENT_LOOP_TEAM,
        "symbol": _AGENT_LOOP_TEAM_SYMBOL,
        "interval": _AGENT_LOOP_INTERVAL,
        "mode": _MODE,
    }


# ---------------------------------------------------------------------------
# Endpoint: aggregated crypto news (Phase 2)
# ---------------------------------------------------------------------------

@app.get("/api/news")
async def api_news(
    limit: int = Query(30, ge=1, le=60),
    sources: str | None = Query(None, description="comma-separated feed ids (coindesk,cointelegraph)"),
) -> dict[str, Any]:
    """Aggregated headlines + sentiment + impact from free RSS feeds."""
    src = [s.strip() for s in sources.split(",") if s.strip()] if sources else None
    items = _news.fetch_news(per_feed=15, sources=src)
    items = items[:limit]
    pos = sum(1 for i in items if i.sentiment == "positive")
    neg = sum(1 for i in items if i.sentiment == "negative")
    neu = sum(1 for i in items if i.sentiment == "neutral")
    impact = [i.to_dict() for i in items if i.impact][:10]
    return {
        "status": "ok",
        "count": len(items),
        "sentiment": {"positive": pos, "negative": neg, "neutral": neu},
        "impact_headlines": impact,
        "items": [i.to_dict() for i in items],
    }


# ---------------------------------------------------------------------------
# Endpoint: Trade Desk — paper positions + orders (Phase 3)
# ---------------------------------------------------------------------------

@app.get("/api/positions")
async def api_positions() -> dict[str, Any]:
    """Paper positions snapshot + auto SL/TP/trailing check.

    In DEMO mode, returns empty snapshot (no execution surface).
    """
    if not _mode_is_real():
        return {
            "cash": 0.0,
            "equity": 0.0,
            "positions": [],
            "open_orders": 0,
            "total_orders": 0,
            "paper_only": True,
            "demo": True,
            "exits": [],
        }
    eng = _paper_engine.get_engine()
    exits = eng.check_exits()
    snap = eng.snapshot()
    snap["exits"] = exits
    snap["audit"] = eng.audit_log[-50:]  # recent PreTradeAdvisory trail
    return snap


@app.post("/api/orders")
async def api_submit_order(payload: dict[str, Any]) -> dict[str, Any]:
    """Submit a PAPER order (buy/sell). Never touches real funds."""
    if not _mode_is_real():
        raise HTTPException(
            status_code=403,
            detail="DEMO mode: execucao desligada. Ative REAL mode para operar.",
        )
    required = ("symbol", "side", "qty")
    if any(k not in payload for k in required):
        raise HTTPException(status_code=400, detail="symbol, side, qty obrigatorios")
    side = str(payload["side"]).lower()
    if side not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="side deve ser buy ou sell")
    try:
        qty = float(payload["qty"])
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="qty invalido")
    if qty <= 0:
        raise HTTPException(status_code=400, detail="qty deve ser > 0")
    from core.paper_engine import Order
    order = Order(
        symbol=str(payload["symbol"]).upper(),
        side=side,
        qty=qty,
        order_type=str(payload.get("order_type", "market")).lower(),
        sl_pct=float(payload["sl_pct"]) if payload.get("sl_pct") else None,
        tp_pct=float(payload["tp_pct"]) if payload.get("tp_pct") else None,
        trailing_pct=float(payload["trailing_pct"]) if payload.get("trailing_pct") else None,
        reason=str(payload.get("reason", ""))[:280],
        advisory=str(payload.get("advisory", ""))[:280],
    )
    result = _paper_engine.get_engine().submit(order)
    _METRICS["orders_paper"] += 1
    status = 200 if result.get("ok") else 400
    return JSONResponse(content=result, status_code=status)


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
