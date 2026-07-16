"""Gerador de séries de preço sintéticas (determinístico, sem rede).

Usado para backtest multi-regime reproduzível: lateral, alta, queda.
Não substitui dados reais — serve para validar comportamento das
estratégias em regimes distintos de forma controlada.
"""
import math
import random


def make_series(
    regime: str,
    n: int = 300,
    seed: int = 42,
    start: float = 100.0,
    vol: float = 0.01,
    drift: float = 0.0,
) -> list[float]:
    """Gera `n` closes.

    regime:
      - "lateral": vol ao redor de start (drift ~0).
      - "uptrend": drift positivo.
      - "downtrend": drift negativo.
    seed: garante reproducibilidade.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if regime not in ("lateral", "uptrend", "downtrend"):
        raise ValueError(f"regime invalido: {regime}")

    rng = random.Random(seed)
    if regime == "uptrend":
        drift = 0.002
    elif regime == "downtrend":
        drift = -0.002

    prices: list[float] = []
    price = float(start)
    for _ in range(n):
        shock = rng.gauss(0, vol)
        price = price * (1 + drift + shock)
        if price <= 0:
            price = start * 0.01  # piso de seguranca
        prices.append(round(price, 2))
    return prices
