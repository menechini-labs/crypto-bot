"""Agent Analyzer — avalia resultados de backtest e emite análise.

Classifica risco (ok / warn / alert) baseado em métricas como
max_drawdown_pct, pnl_pct, sharpe e win_rate. Pode ser usado como
skill do OpenClaw para análise automatizada de estratégias.
"""

from __future__ import annotations

import logging

logger = logging.getLogger('crypto-bot')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

from typing import Any, NamedTuple


class AnalysisResult(NamedTuple):
    """Resultado da análise do agente."""

    assessment: str  # "ok" | "warn" | "alert"
    sharpe: float
    cagr: float
    max_dd: float
    win_rate: float
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            'assessment': self.assessment,
            'sharpe': self.sharpe,
            'cagr': self.cagr,
            'max_dd': self.max_dd,
            'win_rate': self.win_rate,
            'summary': self.summary,
        }


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def analyze_backtest(bt_data: dict[str, Any]) -> AnalysisResult:
    """Analisa um dict de backtest e retorna AnalysisResult com
    classificação de risco."""  # noqa: D205

    pnl = _safe_float(bt_data.get('pnl_pct'))
    dd = _safe_float(bt_data.get('max_drawdown_pct'))
    sharpe = _safe_float(bt_data.get('sharpe'))
    cagr = _safe_float(bt_data.get('cagr'))
    wr = _safe_float(bt_data.get('win_rate'))

    # — Classificação de risco
    if dd > 0.20 or pnl <= 0.0:
        assessment = 'alert'
        summary = _alert_summary(pnl, dd, sharpe)
    elif dd > 0.10 or pnl < 0.05:
        assessment = 'warn'
        summary = _warn_summary(pnl, dd, sharpe)
    else:
        assessment = 'ok'
        summary = _ok_summary(pnl, sharpe, cagr)

    return AnalysisResult(
        assessment=assessment,
        sharpe=round(sharpe, 2),
        cagr=round(cagr, 4),
        max_dd=round(dd, 4),
        win_rate=round(wr, 4),
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Resumos descritivos
# ---------------------------------------------------------------------------


def _alert_summary(pnl: float, dd: float, sharpe: float) -> str:
    if dd > 0.20:
        return (
            f'⚠️  ALERTA: Drawdown critico de {dd:.1%}. '
            f'PnL {pnl:+.1%}, Sharpe {sharpe:.2f}. '
            'Risco de perda irreversivel. Interrompa e reavalie a estrategia.'
        )
    return (
        f'⛔ ALERTA: PnL negativo ({pnl:+.1%}). '
        f'Drawdown {dd:.1%}, Sharpe {sharpe:.2f}. '
        'Estrategia perdendo capital consistentemente.'
    )


def _warn_summary(pnl: float, dd: float, sharpe: float) -> str:
    if dd > 0.10:
        return (
            f'⚠️  ATENCAO: Drawdown elevado ({dd:.1%}). '
            f'PnL {pnl:+.1%}, Sharpe {sharpe:.2f}. '
            'Monitore de perto. Considere reduzir exposicao.'
        )
    return (
        f'⚠️  ATENCAO: PnL baixo ({pnl:+.1%}). '
        f'Sharpe {sharpe:.2f}. '
        'Estrategia com rentabilidade marginal.'
    )


def _ok_summary(pnl: float, sharpe: float, cagr: float) -> str:
    return f'✅ Estrategia saudavel. PnL {pnl:+.1%}, Sharpe {sharpe:.2f}, CAGR {cagr:+.1%}.'
