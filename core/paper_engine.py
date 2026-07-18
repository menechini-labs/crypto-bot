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
from typing import Dict, List, Optional

from core import market as _market
from core.risk import RiskManager

# Persistence file (ledger) — survives restart.
_LEDGER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "paper_ledger.json"
)


@dataclass
class Position:
    symbol: str
    side: str
    qty: float
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_delta: float = 0.0
    highest_price: float = 0.0
    opened_at: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self, mark_price: float = 0.0) -> dict:
        unrealized = (mark_price - self.entry_price) * self.qty if self.side == "long" else 0.0
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

    @classmethod
    def from_dict(cls, d: dict) -> "Position":
        return cls(
            symbol=d["symbol"], side=d.get("side", "long"), qty=float(d["qty"]),
            entry_price=float(d["entry_price"]), stop_loss=d.get("stop_loss"),
            take_profit=d.get("take_profit"), trailing_delta=float(d.get("trailing_delta", 0.0)),
            highest_price=float(d.get("highest_price", d["entry_price"])),
            opened_at=float(d.get("opened_at", time.time())), id=d.get("id", uuid.uuid4().hex[:12]),
        )


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

    @classmethod
    def from_dict(cls, d: dict) -> "Order":
        return cls(
            symbol=d["symbol"], side=d["side"], qty=float(d["qty"]),
            order_type=d.get("order_type", "market"), sl_pct=d.get("sl_pct"),
            tp_pct=d.get("tp_pct"), trailing_pct=d.get("trailing_pct"),
            status=d.get("status", "filled"), reason=d.get("reason", ""),
            created_at=float(d.get("created_at", time.time())), id=d.get("id", uuid.uuid4().hex[:12]),
        )

# Cache de exchangeInfo por symbol (lot size / min notional / tick).
_EXCHANGE_INFO_CACHE: Dict[str, dict] = {}


def _validate_symbol_filters(symbol: str, qty: float, price: float) -> Optional[str]:
    """Validate qty vs LOT_SIZE and notional vs MIN_NOTIONAL from Binance exchangeInfo.

    Returns error string if invalid, None if ok/unknown.
    """
    sym = symbol.upper()
    info = _EXCHANGE_INFO_CACHE.get(sym)
    if info is None:
        try:
            data = _market.fetch_exchange_info(sym)
            filt = {}
            for f in data.get("filters", []):
                filt[f.get("filterType")] = f
            info = filt
        except Exception:
            info = {}  # skip validation if unavailable
        _EXCHANGE_INFO_CACHE[sym] = info

    if not info:
        return None  # cannot validate; allow

    lot = info.get("LOT_SIZE")
    if lot:
        min_qty = float(lot.get("minQty", 0))
        max_qty = float(lot.get("maxQty", 1e18))
        step = float(lot.get("stepSize", 0))
        if qty < min_qty:
            return f"qty {qty} < minQty {min_qty} (LOT_SIZE)"
        if qty > max_qty:
            return f"qty {qty} > maxQty {max_qty} (LOT_SIZE)"
        if step > 0:
            from decimal import Decimal
            try:
                rem = (Decimal(str(qty)) / Decimal(str(step))) % 1
                if float(rem) > 1e-9:
                    return f"qty {qty} nao multiplo de stepSize {step} (LOT_SIZE)"
            except Exception:
                pass

    min_notional = info.get("MIN_NOTIONAL")
    if min_notional:
        mn = float(min_notional.get("minNotional", 0))
        if qty * price < mn:
            return f"notional {qty * price:.2f} < minNotional {mn} (MIN_NOTIONAL)"
    return None


class PaperEngine:
    def __init__(self, cash: float = 1000.0, risk: Optional[RiskManager] = None):
        self.cash = cash
        self.risk = risk or RiskManager()
        self.positions: Dict[str, Position] = {}  # symbol -> position (MVP: 1 per symbol)
        self.orders: List[Order] = []
        self._seen_ids: set = set()
        self._load()

    # --- persistence -----------------------------------------------------
    def _load(self) -> None:
        """Load ledger from disk if present."""
        try:
            if not os.path.exists(_LEDGER_PATH):
                return
            with open(_LEDGER_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.cash = float(data.get("cash", self.cash))
            self.positions = {p["symbol"]: Position.from_dict(p) for p in data.get("positions", [])}
            self.orders = [Order.from_dict(o) for o in data.get("orders", [])]
            self._seen_ids = {o.id for o in self.orders}
        except Exception:
            pass  # start fresh on corruption

    def _save(self) -> None:
        """Persist ledger to disk."""
        try:
            os.makedirs(os.path.dirname(_LEDGER_PATH), exist_ok=True)
            data = {
                "cash": self.cash,
                "positions": [p.to_dict() for p in self.positions.values()],
                "orders": [o.to_dict() for o in self.orders],
            }
            tmp = _LEDGER_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            os.replace(tmp, _LEDGER_PATH)
        except Exception:
            pass  # best-effort persistence

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

        # Exchange instrument filters (lot size / min notional / tick size)
        filter_err = _validate_symbol_filters(order.symbol, order.qty, price)
        if filter_err:
            return {"ok": False, "error": f"filtro exchangeInfo: {filter_err}", "order": order.to_dict()}

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
        self._save()
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
        if exits:
            self._save()
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
