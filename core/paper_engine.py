"""Paper trading engine — simulated positions/orders only. NO real money.

Submits paper orders priced at live Binance ticker (mark-to-market PnL).
Applies the RiskManager gate (max notional, SL/TP, trailing stop) before fill.
Idempotent order ids prevent duplicate submission. State is in-memory (resets
on restart) — this is a simulation surface for the Trade Desk UI, not a ledger.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field

from core import market as _market
from core.risk import RiskManager

# Persistence file (ledger) — survives restart.
_LEDGER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'paper_ledger.json'
)


@dataclass
class Position:
    symbol: str
    side: str
    qty: float
    entry_price: float
    stop_loss: float | None = None
    take_profit: float | None = None
    trailing_delta: float = 0.0
    highest_price: float = 0.0
    opened_at: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self, mark_price: float = 0.0) -> dict:
        unrealized = (mark_price - self.entry_price) * self.qty if self.side == 'long' else 0.0
        return {
            'id': self.id,
            'symbol': self.symbol,
            'side': self.side,
            'qty': round(self.qty, 6),
            'entry_price': round(self.entry_price, 2),
            'mark_price': round(mark_price, 2),
            'stop_loss': round(self.stop_loss, 2) if self.stop_loss else None,
            'take_profit': round(self.take_profit, 2) if self.take_profit else None,
            'unrealized_pnl': round(unrealized, 2),
            'unrealized_pnl_pct': round((unrealized / (self.entry_price * self.qty)) * 100, 2)
            if self.entry_price * self.qty > 0
            else 0.0,
            'opened_at': self.opened_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Position:
        return cls(
            symbol=d['symbol'],
            side=d.get('side', 'long'),
            qty=float(d['qty']),
            entry_price=float(d['entry_price']),
            stop_loss=d.get('stop_loss'),
            take_profit=d.get('take_profit'),
            trailing_delta=float(d.get('trailing_delta', 0.0)),
            highest_price=float(d.get('highest_price', d['entry_price'])),
            opened_at=float(d.get('opened_at', time.time())),
            id=d.get('id', uuid.uuid4().hex[:12]),
        )


@dataclass
class Order:
    symbol: str
    side: str  # "buy" | "sell"
    qty: float
    order_type: str = 'market'  # MVP: market paper
    sl_pct: float | None = None
    tp_pct: float | None = None
    trailing_pct: float | None = None
    status: str = 'filled'  # paper fills instantly at mark
    reason: str = ''
    advisory: str = ''  # PreTradeAdvisoryInterface: rationale recorded before commit
    created_at: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'side': self.side,
            'qty': round(self.qty, 6),
            'order_type': self.order_type,
            'sl_pct': self.sl_pct,
            'tp_pct': self.tp_pct,
            'trailing_pct': self.trailing_pct,
            'status': self.status,
            'reason': self.reason,
            'advisory': self.advisory,
            'created_at': self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Order:
        return cls(
            symbol=d['symbol'],
            side=d['side'],
            qty=float(d['qty']),
            order_type=d.get('order_type', 'market'),
            sl_pct=d.get('sl_pct'),
            tp_pct=d.get('tp_pct'),
            trailing_pct=d.get('trailing_pct'),
            status=d.get('status', 'filled'),
            reason=d.get('reason', ''),
            advisory=d.get('advisory', ''),
            created_at=float(d.get('created_at', time.time())),
            id=d.get('id', uuid.uuid4().hex[:12]),
        )


# Hard safety constants (fail-closed). These mirror Vibe-Trading's signed
# exposure caps + atomic daily order limit.
_MAX_DAILY_ORDERS = int(os.getenv('PAPER_MAX_DAILY_ORDERS', '50'))
_MAX_EXPOSURE_PCT = float(
    os.getenv('PAPER_MAX_EXPOSURE_PCT', '0.95')
)  # max fraction of equity in open positions

# Cache de exchangeInfo por symbol (lot size / min notional / tick).
_EXCHANGE_INFO_CACHE: dict[str, dict] = {}


def _validate_symbol_filters(symbol: str, qty: float, price: float) -> str | None:
    """Validate qty vs LOT_SIZE and notional vs MIN_NOTIONAL from Binance exchangeInfo.

    Returns error string if invalid, None if ok/unknown.
    """
    sym = symbol.upper()
    info = _EXCHANGE_INFO_CACHE.get(sym)
    if info is None:
        try:
            data = _market.fetch_exchange_info(sym)
            filt = {}
            for f in data.get('filters', []):
                filt[f.get('filterType')] = f
            info = filt
        except Exception:
            info = {}  # skip validation if unavailable
        _EXCHANGE_INFO_CACHE[sym] = info

    if not info:
        return None  # cannot validate; allow

    lot = info.get('LOT_SIZE')
    if lot:
        min_qty = float(lot.get('minQty', 0))
        max_qty = float(lot.get('maxQty', 1e18))
        step = float(lot.get('stepSize', 0))
        if qty < min_qty:
            return f'qty {qty} < minQty {min_qty} (LOT_SIZE)'
        if qty > max_qty:
            return f'qty {qty} > maxQty {max_qty} (LOT_SIZE)'
        if step > 0:
            from decimal import Decimal

            try:
                rem = (Decimal(str(qty)) / Decimal(str(step))) % 1
                if float(rem) > 1e-9:
                    return f'qty {qty} nao multiplo de stepSize {step} (LOT_SIZE)'
            except Exception:
                pass

    min_notional = info.get('MIN_NOTIONAL')
    if min_notional:
        mn = float(min_notional.get('minNotional', 0))
        if qty * price < mn:
            return f'notional {qty * price:.2f} < minNotional {mn} (MIN_NOTIONAL)'
    return None


class PaperEngine:
    def __init__(self, cash: float = 1000.0, risk: RiskManager | None = None):
        self.cash = cash
        self.risk = risk or RiskManager()
        self.positions: dict[str, Position] = {}  # symbol -> position (MVP: 1 per symbol)
        self.orders: list[Order] = []
        self.audit_log: list[dict] = []  # PreTradeAdvisoryInterface trail
        self.closed_trades: list[dict] = []  # closed trade history for reflection
        self._day_orders: int = 0
        self._day_key: str = time.strftime('%Y-%m-%d')
        self._seen_ids: set = set()
        self._load()

    # --- persistence -----------------------------------------------------
    def _load(self) -> None:
        """Load ledger from disk if present."""
        try:
            if not os.path.exists(_LEDGER_PATH):
                return
            with open(_LEDGER_PATH, encoding='utf-8') as fh:
                data = json.load(fh)
            self.cash = float(data.get('cash', self.cash))
            self.positions = {
                p['symbol']: Position.from_dict(p) if isinstance(p, dict) else p
                for p in data.get('positions', [])
            }
            # tolerate both dict and dataclass forms
            self.positions = {}
            for p in data.get('positions', []):
                self.positions[p['symbol']] = Position.from_dict(p)
            self.orders = [Order.from_dict(o) for o in data.get('orders', [])]
            self.audit_log = data.get('audit_log', [])
            self.closed_trades = data.get('closed_trades', [])
            self._seen_ids = {o.id for o in self.orders}
            day = data.get('day_key')
            if day == self._day_key:
                self._day_orders = int(data.get('day_orders', 0))
        except Exception:
            pass  # start fresh on corruption

    def _save(self) -> None:
        """Persist ledger to disk."""
        try:
            os.makedirs(os.path.dirname(_LEDGER_PATH), exist_ok=True)
            data = {
                'cash': self.cash,
                'positions': [p.to_dict() for p in self.positions.values()],
                'orders': [o.to_dict() for o in self.orders],
                'audit_log': self.audit_log[-200:],  # cap retained trail
                'closed_trades': self.closed_trades[-200:],  # cap retained history
                'day_orders': self._day_orders,
                'day_key': self._day_key,
            }
            tmp = _LEDGER_PATH + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as fh:
                json.dump(data, fh)
            os.replace(tmp, _LEDGER_PATH)
        except Exception:
            pass  # best-effort persistence

    # --- order submission -------------------------------------------------
    # --- advisory + daily limit gates ----------------------------------
    def _roll_day(self) -> None:
        today = time.strftime('%Y-%m-%d')
        if today != self._day_key:
            self._day_key = today
            self._day_orders = 0

    def _exposure_pct(self, price: float, qty: float) -> float:
        """Total open + proposed notional as fraction of account value.

        Account value = cash + sum(open position qty * mark). This avoids
        double-counting the position notional (equity = cash + unrealized
        PnL already excludes the position's own cost basis).
        """
        marks = {}
        for sym in self.positions:
            try:
                marks[sym] = _market.fetch_ticker(sym)['price']
            except Exception:
                marks[sym] = 0.0
        open_notional = sum(p.qty * marks.get(p.symbol, 0.0) for p in self.positions.values())
        account_value = self.cash + open_notional
        if account_value <= 0:
            return 1.0
        return (open_notional + price * qty) / account_value

    def submit(self, order: Order) -> dict:
        if order.id in self._seen_ids:
            return {'ok': False, 'error': 'ordem duplicada (idempotency)', 'order': order.to_dict()}
        self._seen_ids.add(order.id)

        try:
            ticker = _market.fetch_ticker(order.symbol)
        except Exception as e:
            return {'ok': False, 'error': f'falha ao obter preco: {e}', 'order': order.to_dict()}

        price = ticker['price']
        if price <= 0:
            return {'ok': False, 'error': 'preco invalido', 'order': order.to_dict()}

        # Exchange instrument filters (lot size / min notional / tick size)
        filter_err = _validate_symbol_filters(order.symbol, order.qty, price)
        if filter_err:
            return {
                'ok': False,
                'error': f'filtro exchangeInfo: {filter_err}',
                'order': order.to_dict(),
            }

        # Atomic daily order limit (fail-closed)
        self._roll_day()
        if self._day_orders >= _MAX_DAILY_ORDERS:
            return {
                'ok': False,
                'error': f'limite diario de ordens atingido ({_MAX_DAILY_ORDERS}/dia)',
                'order': order.to_dict(),
            }

        # Signed exposure cap (max fraction of equity in open positions)
        if order.side == 'buy':
            exp_pct = self._exposure_pct(price, order.qty)
            if exp_pct > _MAX_EXPOSURE_PCT:
                return {
                    'ok': False,
                    'error': f'exposicao {exp_pct * 100:.1f}% excede teto {_MAX_EXPOSURE_PCT * 100:.0f}% do equity',
                    'order': order.to_dict(),
                }

        notional = price * order.qty
        max_notional = self.risk.max_notional(self.cash)
        if notional > max_notional:
            return {
                'ok': False,
                'error': f'notional {notional:.2f} excede limite {max_notional:.2f}',
                'order': order.to_dict(),
            }

        # Cancel/close opposite side for same symbol (MVP: single position per symbol)
        if order.side == 'buy':
            if order.symbol in self.positions:
                # already long -> ignore (or average up). MVP: reject duplicate long.
                return {'ok': False, 'error': 'posicao long ja aberta', 'order': order.to_dict()}
            sl = price * (1 - order.sl_pct) if order.sl_pct else None
            tp = price * (1 + order.tp_pct) if order.tp_pct else None
            pos = Position(
                symbol=order.symbol,
                side='long',
                qty=order.qty,
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                trailing_delta=order.trailing_pct or 0.0,
                highest_price=price,
            )
            self.positions[order.symbol] = pos
            self.cash -= notional
        else:  # sell -> close long
            pos = self.positions.get(order.symbol)
            if not pos:
                return {'ok': False, 'error': 'sem posicao para fechar', 'order': order.to_dict()}
            exit_price = price
            entry = pos.entry_price
            pnl = (exit_price - entry) * pos.qty
            pnl_pct = (exit_price - entry) / entry if entry else 0.0
            self.closed_trades.append(
                {
                    'symbol': order.symbol,
                    'side': 'buy',  # entry side
                    'entry_price': round(entry, 2),
                    'exit_price': round(exit_price, 2),
                    'pnl': round(pnl, 2),
                    'pnl_pct': round(pnl_pct, 4),
                    'duration_min': 0.0,
                    'reason': order.reason or 'manual',
                    'exit_ts': time.time(),
                }
            )
            self.cash += price * pos.qty
            del self.positions[order.symbol]

        self.orders.append(order)
        self._day_orders += 1
        # PreTradeAdvisoryInterface: record rationale + risk snapshot.
        self.audit_log.append(
            {
                'ts': time.time(),
                'order_id': order.id,
                'symbol': order.symbol,
                'side': order.side,
                'qty': round(order.qty, 6),
                'price': round(price, 2),
                'reason': order.reason,
                'advisory': order.advisory,
                'exposure_pct': round(self._exposure_pct(0, 0) * 100, 2),
                'day_orders': self._day_orders,
            }
        )
        self._save()
        return {
            'ok': True,
            'order': order.to_dict(),
            'position': pos.to_dict(price) if order.side == 'buy' and pos is not None else None,
        }

    # --- risk maintenance -------------------------------------------------
    def check_exits(self) -> list[dict]:
        """Evaluate SL/TP/trailing for open positions at current mark. Returns exits."""
        exits = []
        for sym, pos in list(self.positions.items()):
            try:
                ticker = _market.fetch_ticker(sym)
            except Exception:
                continue
            price = ticker['price']
            pos.highest_price = max(pos.highest_price, price)

            # Trailing stop: raise SL as price rises.
            if pos.trailing_delta > 0:
                trail_sl = pos.highest_price * (1 - pos.trailing_delta)
                if pos.stop_loss is None or trail_sl > pos.stop_loss:
                    pos.stop_loss = trail_sl

            hit = None
            if pos.stop_loss and price <= pos.stop_loss:
                hit = 'stop_loss'
            elif pos.take_profit and price >= pos.take_profit:
                hit = 'take_profit'

            if hit:
                order = Order(symbol=sym, side='sell', qty=pos.qty, reason=hit)
                res = self.submit(order)
                exits.append({'symbol': sym, 'reason': hit, 'result': res})
        if exits:
            self._save()
        return exits

    # --- snapshots --------------------------------------------------------
    def get_closed_trades(self, since_ts: float | None = None) -> list[dict]:
        """Return closed trade history, optionally filtered by exit timestamp."""
        if since_ts is None:
            return list(self.closed_trades)
        return [t for t in self.closed_trades if t.get('exit_ts', 0) >= since_ts]

    def snapshot(self) -> dict:
        marks = {}
        for sym in self.positions:
            try:
                marks[sym] = _market.fetch_ticker(sym)['price']
            except Exception:
                marks[sym] = 0.0
        positions = [p.to_dict(marks.get(p.symbol, 0.0)) for p in self.positions.values()]
        equity = self.cash + sum(
            (marks.get(p.symbol, 0.0) - p.entry_price) * p.qty for p in self.positions.values()
        )
        return {
            'cash': round(self.cash, 2),
            'equity': round(equity, 2),
            'positions': positions,
            'open_orders': len([o for o in self.orders if o.status == 'open']),
            'total_orders': len(self.orders),
            'paper_only': True,
            'max_exposure_pct': _MAX_EXPOSURE_PCT,
            'max_daily_orders': _MAX_DAILY_ORDERS,
            'day_orders': self._day_orders,
        }


# Module-level singleton (per process). Resets on restart — simulation only.
_engine = PaperEngine()


def get_engine() -> PaperEngine:
    return _engine
