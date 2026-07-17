"""Paper wallet: carteira fictícia em USDT. Nunca toca exchange real.

Regras:
- Compra/venda são apenas anotações locais.
- Toda operação desconta taxa (fee_pct).
- Não permite operar sem caixa/posição suficiente.
"""
import logging

logger = logging.getLogger("crypto-bot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")




class PaperWallet:
    def __init__(self, initial_cash: float = 1000.0, fee_pct: float = 0.001):
        if initial_cash <= 0:
            raise ValueError("initial_cash must be positive")
        if not (0.0 <= fee_pct < 1.0):
            raise ValueError("fee_pct must be in [0, 1)")
        self.cash = float(initial_cash)
        self.fee_pct = float(fee_pct)
        # symbol -> {"qty": float, "avg_price": float}
        self.positions: dict[str, dict] = {}
        self._cycle = 0

    def next_cycle(self) -> int:
        """Incrementa e retorna o contador de ciclo (para o reporter)."""
        self._cycle += 1
        return self._cycle

    def total_equity(self, prices: dict[str, float] | None = None) -> float:
        """Equity total usando preços atuais se fornecidos; senão avg_price."""
        total = self.cash
        for sym, pos in self.positions.items():
            price = (prices or {}).get(sym, pos["avg_price"])
            total += pos["qty"] * price
        return round(total, 8)

    def buy(self, symbol: str, price: float, notional: float) -> float:
        """Compra `notional` em USDT do `symbol` a `price`. Retorna a quantidade."""
        if notional <= 0:
            raise ValueError("notional must be positive")
        if notional > self.cash:
            raise ValueError("insufficient cash")
        qty = (notional * (1 - self.fee_pct)) / price
        self.cash -= notional
        if symbol in self.positions:
            pos = self.positions[symbol]
            total_qty = pos["qty"] + qty
            total_cost = pos["qty"] * pos["avg_price"] + qty * price
            pos["avg_price"] = total_cost / total_qty
            pos["qty"] = total_qty
        else:
            self.positions[symbol] = {"qty": qty, "avg_price": price}
        return qty

    def sell(self, symbol: str, price: float) -> float:
        """Vende toda a posição de `symbol` a `price`. Retorna o valor recebido."""
        if symbol not in self.positions:
            raise ValueError("no position to sell")
        pos = self.positions[symbol]
        proceeds = pos["qty"] * price * (1 - self.fee_pct)
        self.cash += proceeds
        del self.positions[symbol]
        return proceeds

    def position_value(self, symbol: str, current_price: float) -> float:
        if symbol not in self.positions:
            return 0.0
        return self.positions[symbol]["qty"] * current_price

    def equity(self, current_prices: dict[str, float]) -> float:
        total = self.cash
        for sym, pos in self.positions.items():
            price = current_prices.get(sym, pos["avg_price"])
            total += pos["qty"] * price
        return total
