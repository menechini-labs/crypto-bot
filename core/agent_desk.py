"""Agent Desk — multi-agent decision loop (paper-only).

Five lightweight agents run each cycle and publish a transparent verdict:
  - MetricsAgent   : reads live market regime + volatility from cached closes.
  - NewsAgent      : aggregates crypto headlines + sentiment/impact (core.news).
  - RiskAgent      : evaluates current risk-guard thresholds (core.agent_analyzer + risk state).
  - StrategyAgent  : picks/ranks a strategy from the registry for the regime.
  - DecisionCore   : fuses the above into a single buy/sell/hold + confidence.

No LLM required (stdlib only). Designed to be augmented later by an LLM
DecisionCore. Every agent returns a structured record so the UI can render a
"chatroom" of agent reasoning.
"""

from __future__ import annotations

import logging
import time

log = logging.getLogger(__name__)

from dataclasses import dataclass, field

from core import config_loader, scoring
from core import news as news_mod
from core.strategy_registry.registry import get_all


@dataclass
class AgentVerdict:
    name: str
    role: str
    verdict: str  # ok | warn | alert | buy | sell | hold | neutral
    confidence: float  # 0..1
    reasoning: str
    metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'role': self.role,
            'verdict': self.verdict,
            'confidence': round(self.confidence, 3),
            'reasoning': self.reasoning,
            'metrics': self.metrics,
        }


def _metrics_agent(closes: list[float]) -> AgentVerdict:
    if not closes or len(closes) < 20:
        return AgentVerdict(
            'MetricsAgent', 'market', 'neutral', 0.0, 'Sem dados de closes suficientes.', {}
        )
    regime = scoring.detect_regime(closes)
    vol = scoring.calculate_volatility(closes)
    rsi = scoring.rsi(closes)
    vol_state = 'alta' if vol > 0.03 else 'moderada' if vol > 0.015 else 'baixa'
    conf = min(1.0, 0.5 + min(vol, 0.05) * 8)
    return AgentVerdict(
        'MetricsAgent',
        'market',
        'ok',
        conf,
        f'Regime {regime}, volatilidade {vol_state} ({vol:.2%}), RSI {rsi:.1f}.',
        {'regime': regime, 'volatility': round(vol, 4), 'rsi': round(rsi, 2)},
    )


def _news_agent() -> AgentVerdict:
    try:
        snap = news_mod.news_summary(limit=20)
    except Exception as e:  # never block the cycle
        return AgentVerdict(
            'NewsAgent', 'news', 'neutral', 0.0, f'Falha ao obter noticias: {e}', {}
        )
    s = snap.get('sentiment', {})
    pos, neg = s.get('positive', 0), s.get('negative', 0)
    total = max(1, pos + neg + s.get('neutral', 0))
    net = (pos - neg) / total
    verdict = 'ok' if net > 0.1 else 'warn' if net < -0.1 else 'neutral'
    conf = min(1.0, abs(net) + 0.2)
    impact = snap.get('impact_headlines', [])
    reason = f'Sentimento {pos} pos / {neg} neg / {s.get("neutral", 0)} neu'
    if impact:
        reason += f'; {len(impact)} manchete(s) de alto impacto (ex: {impact[0]["title"][:50]}...)'
    return AgentVerdict(
        'NewsAgent',
        'news',
        verdict,
        conf,
        reason,
        {
            'positive': pos,
            'negative': neg,
            'neutral': s.get('neutral', 0),
            'impact_count': len(impact),
        },
    )


def _risk_agent() -> AgentVerdict:
    try:
        cfg = config_loader.load_config()
        risk_cfg = cfg.get('risk', {})
        max_dd = float(risk_cfg.get('max_drawdown_pct', 0.20))
        sl = float(risk_cfg.get('stop_loss_pct', 0.02))
    except Exception:
        max_dd, sl = 0.20, 0.02
    # Paper-only guardrail confirmed; warn if drawdown budget is loose.
    verdict = 'ok' if max_dd <= 0.25 else 'warn'
    conf = 0.9
    reason = (
        f'Risk guard ativo (paper-only). max_drawdown={max_dd:.0%}, '
        f'stop_loss={sl:.0%}. Sem exposição real.'
    )
    return AgentVerdict(
        'RiskAgent',
        'risk',
        verdict,
        conf,
        reason,
        {'max_drawdown_pct': max_dd, 'stop_loss_pct': sl, 'paper_only': True},
    )


def _strategy_agent(closes: list[float]) -> AgentVerdict:
    try:
        strategies = get_all()  # dict: id -> Strategy class
    except Exception:
        strategies = {}
    if not strategies:
        return AgentVerdict(
            'StrategyAgent', 'strategy', 'neutral', 0.0, 'Nenhuma estrategia no registry.', {}
        )
    regime = scoring.detect_regime(closes) if closes else 'unknown'

    def _fit(item):
        sid, cls = item
        name = (cls.__name__ if hasattr(cls, '__name__') else str(sid)).lower()
        if regime in ('lateral', 'volatile') and 'grid' in name:
            return 1.0
        if regime in ('uptrend', 'downtrend') and 'llm' in name:
            return 0.9
        return 0.6

    ranked = sorted(strategies.items(), key=_fit, reverse=True)
    top_id = ranked[0][0]
    conf = _fit(ranked[0])
    return AgentVerdict(
        'StrategyAgent',
        'strategy',
        'ok',
        conf,
        f'Regime {regime}: melhor fit = {top_id}.',
        {'regime': regime, 'top': top_id, 'candidates': [s[0] for s in ranked[:3]]},
    )


def _decision_core(agents: list[AgentVerdict], closes: list[float]) -> AgentVerdict:
    # Weighted fusion: metrics + strategy push direction; news + risk gate.
    # Missing agents are skipped (handles team presets).
    def _find(name: str) -> AgentVerdict | None:
        return next((a for a in agents if a.name == name), None)

    metrics = _find('MetricsAgent')
    news = _find('NewsAgent')
    risk = _find('RiskAgent')
    strat = _find('StrategyAgent')

    # Base signal from regime + strategy fit.
    if metrics:
        regime = (
            metrics.metrics.get('regime', 'unknown') if hasattr(metrics, 'metrics') else 'unknown'
        )
    else:
        regime = 'unknown'

    if regime == 'uptrend':
        base = 0.7
    elif regime == 'downtrend':
        base = 0.3
    else:
        base = 0.5

    if strat:
        base = base * 0.7 + strat.confidence * 0.3

    # News tilt.
    if news:
        if news.verdict == 'ok':
            base += 0.1
        elif news.verdict == 'warn':
            base -= 0.15

    # Risk gate: hard block if risk warns AND drawdown budget loose.
    if risk and risk.verdict == 'warn':
        base *= 0.8

    base = max(0.0, min(1.0, base))
    if base >= 0.6:
        verdict = 'buy'
    elif base <= 0.4:
        verdict = 'sell'
    else:
        verdict = 'hold'
    conf = round(base, 3)
    parts = [f'regime={regime}']
    if metrics:
        parts.append(f'metrics={metrics.confidence:.2f}')
    if strat:
        parts.append(f'strat={strat.metrics.get("top", "?")} ({strat.confidence:.2f})')
    if news:
        parts.append(f'news={news.verdict} ({news.confidence:.2f})')
    if risk:
        parts.append(f'risk={risk.verdict}')
    parts.append(f'-> {verdict.upper()} @ {conf:.2f}')
    reason = ' | '.join(parts)
    return AgentVerdict(
        'DecisionCore', 'fusion', verdict, conf, reason, {'regime': regime, 'fused_score': conf}
    )


def _llm_decision_core(agents: list[AgentVerdict], closes: list[float]) -> AgentVerdict:
    """LLM-augmented DecisionCore. Uses 9router LLM to fuse agent signals.

    Falls back to rule-based _decision_core if LLM disabled or errors.
    """
    from core import llm_client

    if not llm_client.is_enabled():
        return _decision_core(agents, closes)
    ctx = '\n'.join(
        f'- {a.name}: {a.verdict} (conf {a.confidence:.2f}) — {a.reasoning}' for a in agents
    )
    prompt = (
        'You are a crypto day-trading decision core. Given these agent signals, '
        'decide BUY, SELL or HOLD for BTC/USDT. Reply with one word (buy/sell/hold) '
        'followed by a confidence 0.0-1.0 and a short reason.\n\n'
        f'AGENT SIGNALS:\n{ctx}\n\n'
        'Format: <buy|sell|hold> <0.0-1.0> <reason>'
    )
    try:
        raw = llm_client.chat(prompt, max_tokens=80, temperature=0.2)
        toks = raw.replace(',', ' ').split()
        word = next((t for t in toks if t in ('buy', 'sell', 'hold')), 'hold')
        conf_tok = next((t for t in toks if t.replace('.', '').isdigit()), '0.5')
        try:
            conf = max(0.0, min(1.0, float(conf_tok)))
        except ValueError:
            conf = 0.5
        reason = f'[LLM] {raw.strip()}'
        return AgentVerdict(
            'LLMDecisionCore',
            'fusion-llm',
            word,
            round(conf, 3),
            reason,
            {'llm': True, 'raw': raw[:200]},
        )
    except Exception as e:
        log.warning('LLMDecisionCore fallback (rule-based): %s', e)
        return _decision_core(agents, closes)


def _fetch_fallback_closes() -> list[float]:
    """Fallback: fetch BTCUSDT 1h closes for agent cycles."""
    try:
        from core.market import fetch_ohlcv

        candles = fetch_ohlcv('BTCUSDT', '1h', 100)
        return [c['close'] for c in candles]
    except Exception:
        return []


def run_team(preset: dict, closes: list[float] | None = None) -> dict:
    """Run a cycle using only the agents named in `preset['agents']`.

    preset: dict retornado por core.swarm_presets.get_preset()
    """
    if not closes:
        closes = _fetch_fallback_closes()
    t0 = time.time()
    allowed = set(preset.get('agents', []))
    # mapa nome -> factory
    registry = {
        'MetricsAgent': lambda: _metrics_agent(closes),
        'NewsAgent': lambda: _news_agent(),
        'RiskAgent': lambda: _risk_agent(),
        'StrategyAgent': lambda: _strategy_agent(closes),
    }
    all_agents = [registry[n]() for n in allowed if n in registry]
    if 'DecisionCore' in allowed:
        core = _llm_decision_core(all_agents, closes)
        all_agents.append(core)
    else:
        core = None
    return {
        'status': 'ok',
        'team': preset.get('name'),
        'cycle_id': int(t0 * 1000),
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'paper_only': True,
        'agents': [a.to_dict() for a in all_agents],
        'decision': core.to_dict() if core else None,
    }


def run_cycle(closes: list[float] | None = None) -> dict:
    """Run a full Agent Desk cycle. Returns serializable dict for the API."""
    if not closes:
        closes = _fetch_fallback_closes()
    t0 = time.time()
    agents = [
        _metrics_agent(closes),
        _news_agent(),
        _risk_agent(),
        _strategy_agent(closes),
    ]
    core = _llm_decision_core(agents, closes)
    agents.append(core)
    return {
        'status': 'ok',
        'cycle_id': int(t0 * 1000),
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'paper_only': True,
        'agents': [a.to_dict() for a in agents],
        'decision': core.to_dict(),
    }


def _should_execute_decision(decision: AgentVerdict) -> bool:
    """Only buy/sell with confidence >= 0.5 get executed (hold is skipped)."""
    return decision.verdict in ('buy', 'sell') and decision.confidence >= 0.5


def _compute_qty(symbol: str, confidence: float, available_cash: float) -> float:
    """qty = available_cash * confidence / last_price, rounded to LOT_SIZE stepSize."""
    try:
        from core import market as _mkt

        price = float(_mkt.fetch_ticker(symbol)['price'])
    except Exception:
        price = 0.0
    if price <= 0:
        return 0.0
    notional = available_cash * confidence
    qty = notional / price
    # respect RiskManager max_notional (round down)
    try:
        from core.risk import RiskManager

        max_not = RiskManager().max_notional(available_cash)
        if notional > max_not:
            notional = max_not * 0.95
            qty = notional / price
    except Exception:
        pass
    # round to 6 decimals first
    qty = float(f'{qty:.6f}')
    # enforce minQty + stepSize from exchangeInfo
    try:
        from core.paper_engine import _EXCHANGE_INFO_CACHE

        sym = symbol.upper()
        info = _EXCHANGE_INFO_CACHE.get(sym)
        if info is None:
            try:
                data = _mkt.fetch_exchange_info(sym)
                filt = {f.get('filterType'): f for f in data.get('filters', [])}
                info = filt
                _EXCHANGE_INFO_CACHE[sym] = filt
            except Exception:
                info = {}
        lot = info.get('LOT_SIZE') if info else None
        if lot:
            min_qty = float(lot.get('minQty', 0))
            step = float(lot.get('stepSize', 0))
            qty = max(qty, min_qty)
            if step > 0:
                from decimal import Decimal

                qty = float(
                    (Decimal(str(qty)) / Decimal(str(step))).to_integral_value()
                    * Decimal(str(step))
                )
                qty = float(f'{qty:.6f}')
        # re-validate notional after step rounding
        final_notional = qty * price
        if final_notional > max_not:
            # reduce one step
            if step > 0:
                qty = float((Decimal(str(qty)) - Decimal(str(step))).quantize(Decimal(str(step))))
                qty = float(f'{qty:.6f}')
    except Exception:
        pass
    return qty


def execute_cycle(
    closes: list[float] | None = None, symbol: str = 'BTCUSDT', mode: str = 'demo'
) -> dict:
    """Run a cycle and submit the decision to PaperEngine if REAL mode.

    Returns the cycle dict plus an `execution` field with the result.
    In DEMO mode, execution is skipped (paper_only decision only).
    """
    cycle = run_cycle(closes)
    decision = cycle['decision']
    verdict = decision['verdict'] if isinstance(decision, dict) else decision.verdict
    conf = decision['confidence'] if isinstance(decision, dict) else decision.confidence

    if mode != 'real' or not _should_execute_decision(
        AgentVerdict(
            decision['name'],
            decision['role'],
            decision['verdict'],
            decision['confidence'],
            decision['reasoning'],
            decision.get('metrics', {}),
        )
    ):
        cycle['execution'] = {
            'executed': False,
            'reason': 'DEMO mode'
            if mode != 'real'
            else f'decisao {verdict} ignorada (conf={conf:.2f})',
        }
        return cycle

    # REAL mode: submit order
    from core import paper_engine as _paper

    engine = _paper.get_engine()
    snap = engine.snapshot()
    available = snap.get('available_cash') or snap.get('cash', 0.0)
    qty = _compute_qty(symbol, conf, available)
    if qty <= 0:
        cycle['execution'] = {
            'executed': False,
            'reason': 'qty calculado <= 0 (sem caixa ou preco?)',
        }
        return cycle
    order = _paper.Order(
        symbol=symbol,
        side=verdict,
        qty=qty,
        sl_pct=0.02,
        tp_pct=0.05,
        trailing_pct=0.01,
        reason=f'AgentDesk {verdict} (conf {conf:.2f})',
        advisory=decision.get('reasoning', ''),
    )
    result = engine.submit(order)
    cycle['execution'] = {
        'executed': bool(result.get('ok')),
        'order_id': result.get('order', {}).get('id'),
        'result': result,
        'qty': qty,
    }
    return cycle
