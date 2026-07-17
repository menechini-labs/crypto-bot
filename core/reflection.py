"""ReflectionAgent — analisa trades fechados, identifica padroes, gera insights.

Pos-backtest ou runtime, analisa trades fechados para:
- Padroes de erro (perdeu em qual regime, lado, duracao)
- Calibragem de confianca
- Recomendacoes de ajuste de parametros
- Serializa reflexoes em data/reflections.json

Sem dependencias externas.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

_REFLECTIONS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "reflections.json",
)


def _safe(val: Any, default: float = 0.0) -> float:
    try:
        v = float(val)
        return v if v == v else default
    except (ValueError, TypeError):
        return default


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2.0
    return s[mid]


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def reflect_trades(
    trades: list[dict[str, Any]],
    regime: str = "unknown",
    strategy: str = "unknown",
    symbol: str = "unknown",
) -> dict[str, Any]:
    """Analisa lista de trades fechados, retorna insights estruturados.

    Cada trade: {"side", "entry_price", "exit_price", "pnl", "pnl_pct", "duration_min"}
    """
    if not trades:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "regime": regime,
            "strategy": strategy,
            "symbol": symbol,
            "total_trades": 0,
            "insights": [],
            "metrics": {},
            "patterns": [],
            "recommendations": [],
        }

    winners = [t for t in trades if _safe(t.get("pnl")) > 0]
    losers = [t for t in trades if _safe(t.get("pnl")) <= 0]
    total = len(trades)
    win_count = len(winners)
    loss_count = len(losers)

    win_rate = win_count / total if total else 0.0
    avg_winner = _mean([_safe(t.get("pnl_pct")) for t in winners]) if winners else 0.0
    avg_loser = _mean([_safe(t.get("pnl_pct")) for t in losers]) if losers else 0.0
    total_pnl = sum(_safe(t.get("pnl")) for t in trades)
    total_pnl_pct = sum(_safe(t.get("pnl_pct")) for t in trades)

    durations = [
        _safe(t.get("duration_min"))
        for t in trades
        if _safe(t.get("duration_min")) > 0
    ]
    avg_duration = _mean(durations) if durations else 0.0
    median_duration = _median(durations) if durations else 0.0

    max_consecutive_losses = 0
    current_streak = 0
    for t in trades:
        if _safe(t.get("pnl")) <= 0:
            current_streak += 1
            max_consecutive_losses = max(max_consecutive_losses, current_streak)
        else:
            current_streak = 0

    buys = [t for t in trades if t.get("side", "").lower() == "buy"]
    sells = [t for t in trades if t.get("side", "").lower() == "sell"]
    buy_win_rate = (
        sum(1 for t in buys if _safe(t.get("pnl")) > 0) / len(buys) if buys else 0.0
    )
    sell_win_rate = (
        sum(1 for t in sells if _safe(t.get("pnl")) > 0) / len(sells)
        if sells
        else 0.0
    )

    insights: list[str] = []

    if win_rate >= 0.6:
        insights.append(
            f"Win rate {win_rate:.0%} — saudavel, acima de 60%."
        )
    elif win_rate >= 0.45:
        insights.append(
            f"Win rate {win_rate:.0%} — mediano. Avaliar relacao win/loss."
        )
    else:
        insights.append(
            f"Win rate {win_rate:.0%} — baixo. Revisar setup de entrada."
        )

    if avg_winner > 0 and avg_loser < 0:
        ratio = abs(avg_winner / avg_loser) if avg_loser != 0 else float("inf")
        if ratio > 2:
            insights.append(
                f"Relacao ganho/perda {ratio:.1f}x — winners muito maiores que losers. Bom."
            )
        elif ratio > 1:
            insights.append(
                f"Relacao ganho/perda {ratio:.1f}x — equilibrado."
            )
        else:
            insights.append(
                f"Relacao ganho/perda {ratio:.1f}x — losers maiores que winners. "
                "Aumentar stop-loss ou reduzir alvos."
            )

    if max_consecutive_losses >= 5:
        insights.append(
            f"{max_consecutive_losses} perdas consecutivas — risco de serie. "
            "Considerar pausa apos 3 perdas seguidas."
        )
    elif max_consecutive_losses >= 3:
        insights.append(
            f"{max_consecutive_losses} perdas consecutivas — aceitavel, mas monitorar."
        )
    else:
        insights.append(
            f"Maximo de perdas consecutivas: {max_consecutive_losses} — controle ok."
        )

    if buys and sells:
        diff = abs(buy_win_rate - sell_win_rate)
        if diff > 0.15:
            better = "compra" if buy_win_rate > sell_win_rate else "venda"
            insights.append(
                f"Vies significativo para {better} "
                f"(buy {buy_win_rate:.0%} vs sell {sell_win_rate:.0%}). "
                "Estrategia direcional?"
            )

    if avg_duration > 0:
        if avg_duration > 1440:
            insights.append(
                f"Duracao media {avg_duration:.0f}min — trades longos. "
                "Sensibilidade a overnight risk?"
            )
        elif avg_duration < 60:
            insights.append(
                f"Duracao media {avg_duration:.0f}min — trades muito curtos. "
                "Cuidado com noise no timeframe."
            )
        else:
            insights.append(
                f"Duracao media {avg_duration:.0f}min — adequada."
            )

    if total_pnl > 0:
        insights.append(
            f"PnL total +{total_pnl:.2f} USDT ({total_pnl_pct:+.2%}) — "
            "estrategia lucrativa no periodo."
        )
    else:
        insights.append(
            f"PnL total {total_pnl:.2f} USDT ({total_pnl_pct:+.2%}) — "
            "estrategia nao lucrativa. Revisar."
        )

    patterns: list[dict[str, Any]] = []

    # Perdas recentes
    recent_losers = 0
    for t in reversed(trades[-10:]):
        if _safe(t.get("pnl")) <= 0:
            recent_losers += 1
        else:
            break
    if recent_losers >= 3:
        patterns.append(
            {
                "type": "recent_decline",
                "severity": "warn",
                "description": f"Ultimos {recent_losers} trades foram perdas. "
                "Possivel mudanca de regime ou fadiga da estrategia.",
                "count": recent_losers,
            }
        )

    # Perdedores duram mais
    if losers and durations:
        loser_durations = [
            _safe(t.get("duration_min"))
            for t in losers
            if _safe(t.get("duration_min")) > 0
        ]
        if loser_durations:
            avg_loser_dur = _mean(loser_durations)
            avg_winner_dur = (
                _mean(
                    [
                        _safe(t.get("duration_min"))
                        for t in winners
                        if _safe(t.get("duration_min")) > 0
                    ]
                )
                if winners
                else 0
            )
            if avg_winner_dur > 0 and avg_loser_dur > avg_winner_dur * 1.5:
                patterns.append(
                    {
                        "type": "loser_holds_too_long",
                        "severity": "warn",
                        "description": f"Perdedores duram {avg_loser_dur:.0f}min "
                        f"vs ganhadores {avg_winner_dur:.0f}min. "
                        "Stop-loss muito largo ou hesitacao em cortar.",
                        "loser_avg_duration_min": round(avg_loser_dur, 1),
                        "winner_avg_duration_min": round(avg_winner_dur, 1),
                    }
                )

    # Lucro concentrado
    if winners:
        pnls = sorted([_safe(t.get("pnl")) for t in winners], reverse=True)
        top3 = sum(pnls[:3])
        if total_pnl > 0 and top3 / total_pnl > 0.5:
            patterns.append(
                {
                    "type": "concentrated_gains",
                    "severity": "info",
                    "description": f"Top 3 trades = {top3/total_pnl:.0%} do PnL total. "
                    "Lucro concentrado em poucos acertos.",
                    "top3_pnl_share": round(top3 / total_pnl, 3)
                    if total_pnl != 0
                    else 0,
                }
            )

    # Performance por regime
    regimes_found: dict[str, list[float]] = {}
    for t in trades:
        r = t.get("regime", regime)
        regimes_found.setdefault(r, []).append(_safe(t.get("pnl_pct")))
    regime_perf = {}
    for r, pnls_list in regimes_found.items():
        regime_perf[r] = {
            "trades": len(pnls_list),
            "avg_pnl_pct": round(_mean(pnls_list), 4),
            "win_rate": (
                round(sum(1 for p in pnls_list if p > 0) / len(pnls_list), 3)
                if pnls_list
                else 0
            ),
        }
        if len(pnls_list) >= 3 and _mean(pnls_list) < -0.01:
            patterns.append(
                {
                    "type": "regime_weakness",
                    "severity": "warn",
                    "description": f"Estrategia perde em regime '{r}' "
                    f"(avg {_mean(pnls_list):+.2%} em {len(pnls_list)} trades). "
                    "Considere filtrar este regime.",
                    "regime": r,
                    "avg_pnl_pct": round(_mean(pnls_list), 4),
                    "trades": len(pnls_list),
                }
            )

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "regime": regime,
        "strategy": strategy,
        "symbol": symbol,
        "total_trades": total,
        "insights": insights,
        "patterns": patterns,
        "metrics": {
            "win_rate": round(win_rate, 3),
            "avg_winner_pct": round(avg_winner, 4),
            "avg_loser_pct": round(avg_loser, 4),
            "profit_factor": (
                round(abs(avg_winner / avg_loser), 3) if avg_loser != 0 else float("inf")
            ),
            "total_pnl": round(total_pnl, 4),
            "total_pnl_pct": round(total_pnl_pct, 4),
            "max_consecutive_losses": max_consecutive_losses,
            "avg_duration_min": round(avg_duration, 1),
            "median_duration_min": round(median_duration, 1),
            "buy_win_rate": round(buy_win_rate, 3),
            "sell_win_rate": round(sell_win_rate, 3),
            "regime_performance": regime_perf,
        },
        "recommendations": _generate_recommendations(insights, patterns),
    }


def _generate_recommendations(
    insights: list[str], patterns: list[dict[str, Any]]
) -> list[str]:
    recs: list[str] = []
    has_recent_decline = any(p["type"] == "recent_decline" for p in patterns)
    has_loser_holds = any(p["type"] == "loser_holds_too_long" for p in patterns)
    has_concentrated = any(p["type"] == "concentrated_gains" for p in patterns)
    has_regime_weakness = any(p["type"] == "regime_weakness" for p in patterns)

    for ins in insights:
        if "perda" in ins.lower() and "consecutivo" in ins.lower() and "5" in ins:
            recs.append(
                "Adicionar circuit breaker: pausar trading apos 3 perdas consecutivas."
            )
        elif "relacao" in ins.lower() and "1x" in ins and "menor" in ins:
            recs.append("Ajustar take-profit para pelo menos 2x o stop-loss.")

    if has_regime_weakness:
        recs.append(
            "Adicionar filtro de regime: evitar operar em regimes onde "
            "a estrategia tem desempenho negativo."
        )
    if has_loser_holds:
        recs.append(
            "Reduzir stop-loss percentual ou implementar trailing stop "
            "para cortar perdas mais cedo."
        )
    if has_concentrated:
        recs.append(
            "Verificar se a estrategia nao esta overfitting — lucro concentrado "
            "em poucos trades sugere baixa robustez."
        )
    if has_recent_decline and has_regime_weakness:
        recs.append(
            "POSSIVEL MUDANCA DE REGIME. Reavaliar seletor de estrategia."
        )

    return recs


def save_reflection(reflection: dict[str, Any]) -> str:
    """Salva reflexao em data/reflections.json. Retorna path."""
    os.makedirs(os.path.dirname(_REFLECTIONS_FILE), exist_ok=True)
    history: list[dict[str, Any]] = []
    if os.path.exists(_REFLECTIONS_FILE):
        try:
            with open(_REFLECTIONS_FILE) as f:
                data = json.load(f)
                if isinstance(data, list):
                    history = data
        except (json.JSONDecodeError, OSError):
            pass
    history.append(reflection)
    if len(history) > 50:
        history = history[-50:]
    with open(_REFLECTIONS_FILE, "w") as f:
        json.dump(history, f, indent=2)
    return _REFLECTIONS_FILE


def load_reflections(limit: int = 10) -> list[dict[str, Any]]:
    """Carrega ultimas N reflexoes do arquivo."""
    if not os.path.exists(_REFLECTIONS_FILE):
        return []
    try:
        with open(_REFLECTIONS_FILE) as f:
            data = json.load(f)
            if isinstance(data, list):
                return data[-limit:]
    except (json.JSONDecodeError, OSError):
        pass
    return []
