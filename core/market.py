"""Coleta de dados de mercado via API PÚBLICA da Binance (sem autenticação).

Usa apenas urllib (stdlib). Retorna velas OHLCV. Nenhuma credencial necessária.
"""
import logging

logger = logging.getLogger("crypto-bot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


import json
import urllib.error
import urllib.request


def fetch_ohlcv(symbol: str, timeframe: str = "1h", limit: int = 100) -> list[dict]:
    """Retorna lista de velas: {"ts", "open", "high", "low", "close", "volume"}.

    symbol no formato Binance, ex: "BTC/USDT" -> "BTCUSDT".
    """
    logger.info("fetch_ohlcv symbol=%s timeframe=%s limit=%d", symbol, timeframe, limit)
    pair = symbol.replace("/", "").upper()
    url = (
        f"https://api.binance.com/api/v3/klines"
        f"?symbol={pair}&interval={timeframe}&limit={limit}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "crypto-bot-paper/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(f"market data fetch failed for {symbol}: {e}") from e

    candles = []
    for row in raw:
        candles.append(
            {
                "ts": int(row[0]),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            }
        )
    return candles

def fetch_ticker(symbol: str) -> dict:
    """Preço atual + stats 24h via API pública Binance (sem auth).

    Retorna {"symbol", "price", "change_pct_24h", "high_24h", "low_24h", "volume_24h"}.
    """
    pair = symbol.replace("/", "").upper()
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={pair}"
    req = urllib.request.Request(url, headers={"User-Agent": "crypto-bot-paper/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(f"ticker fetch failed for {symbol}: {e}") from e
    return {
        "symbol": raw.get("symbol", pair),
        "price": float(raw.get("lastPrice", 0.0)),
        "change_pct_24h": float(raw.get("priceChangePercent", 0.0)),
        "high_24h": float(raw.get("highPrice", 0.0)),
        "low_24h": float(raw.get("lowPrice", 0.0)),
        "volume_24h": float(raw.get("volume", 0.0)),
    }


def fetch_exchange_info(symbol: str) -> dict:
    """Binance exchangeInfo para um symbol (filtros LOT_SIZE / MIN_NOTIONAL etc).

    Retorna dict com "filters" (lista de filtros). Sem auth.
    """
    pair = symbol.replace("/", "").upper()
    url = f"https://api.binance.com/api/v3/exchangeInfo?symbol={pair}"
    req = urllib.request.Request(url, headers={"User-Agent": "crypto-bot-paper/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(f"exchangeInfo fetch failed for {symbol}: {e}") from e
    syms = raw.get("symbols") or []
    return syms[0] if syms else {"filters": []}


def fetch_depth(symbol: str, limit: int = 50) -> dict:
    """Order book (bids/asks) via API pública Binance (sem auth).

    Retorna {"symbol", "bids": [[price, qty], ...], "asks": [[price, qty], ...]}.
    """
    pair = symbol.replace("/", "").upper()
    url = f"https://api.binance.com/api/v3/depth?symbol={pair}&limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "crypto-bot-paper/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(f"depth fetch failed for {symbol}: {e}") from e
    bids = [[float(p), float(q)] for p, q in raw.get("bids", [])]
    asks = [[float(p), float(q)] for p, q in raw.get("asks", [])]
    return {"symbol": pair, "bids": bids, "asks": asks}
