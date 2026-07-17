"""Coleta de dados de mercado via API PÚBLICA da Binance (sem autenticação).

Usa apenas urllib (stdlib). Retorna velas OHLCV. Nenhuma credencial necessária.
"""
import logging

logger = logging.getLogger("crypto-bot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


import json
import urllib.request
import urllib.error


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
