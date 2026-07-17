"""Paper trading engine — simulated positions/orders only. NO real money.

Submits paper orders priced at live Binance ticker (mark-to-market PnL).
Applies the RiskManager gate (max notional, SL/TP, trailing stop) before fill.
Idempotent order ids prevent duplicate submission. State is in-memory (resets
on restart) — this is a simulation surface for the Trade Desk UI, not a ledger.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core import market as _market
from core.risk import RiskManager


@dataclass
class Position:
    symbol: str
    side: str  # "long" | "short" (MVP: long only)
    qty: float
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_delta: float = 0.0
    highest_price: float = 0.0
    opened_at: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self, mark_price: float = 0.0) -> dict:
        unrealized = 0.0
        if self.qty > 0 and self.entry_price > 0:
            unrealized = (mark_price - self.entry_price) * self.qty
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side,
            "qty": round(self.qty, 6),
            "entry_price": round(self.entry_price, 2),
            "mark_price": round(mark_price, 2),
            "stop_loss": round(self.stop_loss, 2) if self.stop_loss else None,
            "take_profit": round(self.take_profit, 2) if self.take_profit else None,
            "unrealized_pnl": round(unrealized, 2),
            "unrealized_pnl_pct": round((unrealized / (self.entry_price * self.qty)) * 100, 2)
            if self.entry_price * self.qty > 0 else 0.0,
            "opened_at": self.opened_at,
        }


@dataclass
class Order:
    symbol: str
    side: str  # "buy" | "sell"
    qty: float
    order_type: str = "market"  # MVP: market paper
    sl_pct: Optional[float] = None
    tp_pct: Optional[float] = None
    trailing_pct: Optional[float] = None
    status: str = "filled"  # paper fills instantly at mark
    reason: str = ""
    created_at: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side,
            "qty": round(self.qty, 6),
            "order_type": self.order_type,
            "sl_pct": self.sl_pct,
            "tp_pct": self.tp_pct,
            "trailing_pct": self.trailing_pct,
            "status": self.status,
            "reason": self.reason,
            "created_at": self.created_at,
        }


class PaperEngine:
    def __init__(self, cash: float = 1000.0, risk: Optional[RiskManager] = None):
        self.cash = cash
        self.risk = risk or RiskManager()
        self.positions: Dict[str, Position] = {}  # symbol -> position (MVP: 1 per symbol)
        self.orders: List[Order] = []
        self._seen_ids: set = set()

    # --- order submission -------------------------------------------------
    def submit(self, order: Order) -> dict:
        if order.id in self._seen_ids:
            return {"ok": False, "error": "ordem duplicada (idempotency)", "order": order.to_dict()}
        self._seen_ids.add(order.id)

        try:
            ticker = _market.fetch_ticker(order.symbol)
        except Exception as e:
            return {"ok": False, "error": f"falha ao obter preco: {e}", "order": order.to_dict()}

        price = ticker["price"]
        if price <= 0:
            return {"ok": False, "error": "preco invalido", "order": order.to_dict()}

        notional = price * order.qty
        max_notional = self.risk.max_notional(self.cash)
        if notional > max_notional:
            return {
                "ok": False,
                "error": f"notional {notional:.2f} excede limite {max_notional:.2f}",
                "order": order.to_dict(),
            }

        # Cancel/close opposite side for same symbol (MVP: single position per symbol)
        if order.side == "buy":
            if order.symbol in self.positions:
                # already long -> ignore (or average up). MVP: reject duplicate long.
                return {"ok": False, "error": "posicao long ja aberta", "order": order.to_dict()}
            sl = price * (1 - order.sl_pct) if order.sl_pct else None
            tp = price * (1 + order.tp_pct) if order.tp_pct else None
            pos = Position(
                symbol=order.symbol, side="long", qty=order.qty,
                entry_price=price, stop_loss=sl, take_profit=tp,
                trailing_delta=order.trailing_pct or 0.0, highest_price=price,
            )
            self.positions[order.symbol] = pos
            self.cash -= notional
        else:  # sell -> close long
            pos = self.positions.get(order.symbol)
            if not pos:
                return {"ok": False, "error": "sem posicao para fechar", "order": order.to_dict()}
            self.cash += price * pos.qty
            del self.positions[order.symbol]

        self.orders.append(order)
        return {"ok": True, "order": order.to_dict(), "position": self.positions.get(order.symbol).to_dict(price) if order.side == "buy" else None}

    # --- risk maintenance -------------------------------------------------
    def check_exits(self) -> List[dict]:
        """Evaluate SL/TP/trailing for open positions at current mark. Returns exits."""
        exits = []
        for sym, pos in list(self.positions.items()):
            try:
                ticker = _market.fetch_ticker(sym)
            except Exception:
                continue
            price = ticker["price"]
            pos.highest_price = max(pos.highest_price, price)

            # Trailing stop: raise SL as price rises.
            if pos.trailing_delta > 0:
                trail_sl = pos.highest_price * (1 - pos.trailing_delta)
                if pos.stop_loss is None or trail_sl > pos.stop_loss:
                    pos.stop_loss = trail_sl

            hit = None
            if pos.stop_loss and price <= pos.stop_loss:
                hit = "stop_loss"
            elif pos.take_profit and price >= pos.take_profit:
                hit = "take_profit"

            if hit:
                order = Order(symbol=sym, side="sell", qty=pos.qty, reason=hit)
                res = self.submit(order)
                exits.append({"symbol": sym, "reason": hit, "result": res})
        return exits

    # --- snapshots --------------------------------------------------------
    def snapshot(self) -> dict:
        marks = {}
        for sym in self.positions:
            try:
                marks[sym] = _market.fetch_ticker(sym)["price"]
            except Exception:
                marks[sym] = 0.0
        positions = [p.to_dict(marks.get(p.symbol, 0.0)) for p in self.positions.values()]
        equity = self.cash + sum(
            (marks.get(p.symbol, 0.0) - p.entry_price) * p.qty for p in self.positions.values()
        )
        return {
            "cash": round(self.cash, 2),
            "equity": round(equity, 2),
            "positions": positions,
            "open_orders": len([o for o in self.orders if o.status == "open"]),
            "total_orders": len(self.orders),
            "paper_only": True,
        }


# Module-level singleton (per process). Resets on restart — simulation only.
_engine = PaperEngine()


def get_engine() -> PaperEngine:
    return _engine
