"""Executor de ordens.

POR SEGURANÇA: este módulo é PAPER ONLY por padrão. Live trading só é
permitido se (a) mode="live" E (b) a variável de ambiente ALLOW_LIVE_TRADING=1
estiver explicitamente setada. Mesmo assim, este arquivo NÃO envia ordens
para nenhuma exchange — cabe ao integrador acoplar a API real e revisar o código.
"""
import os


class PaperExecutor:
    def __init__(self, mode: str = "paper"):
        if mode not in ("paper", "live"):
            raise ValueError("mode must be 'paper' or 'live'")
        if mode == "live" and os.environ.get("ALLOW_LIVE_TRADING") != "1":
            raise RuntimeError(
                "Live trading blocked. Set ALLOW_LIVE_TRADING=1 explicitly to enable."
            )
        self.mode = mode

    def execute_buy(self, symbol: str, price: float, notional: float) -> dict:
        # Simulação local. Nenhuma chamada de rede.
        return {
            "symbol": symbol,
            "side": "buy",
            "price": price,
            "notional": notional,
            "live": self.mode == "live",
            "status": "simulated" if self.mode == "paper" else "LIVE_PENDING_REVIEW",
        }

    def execute_sell(self, symbol: str, price: float) -> dict:
        return {
            "symbol": symbol,
            "side": "sell",
            "price": price,
            "live": self.mode == "live",
            "status": "simulated" if self.mode == "paper" else "LIVE_PENDING_REVIEW",
        }
