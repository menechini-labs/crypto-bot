"""Reporter de equity/PnL (dashboard local em JSON).

Stdlib puro. Registra um snapshot por ciclo do bot em modo contínuo,
para acompanhamento sem depender da CLI. Sem rede, sem risco.
"""

import logging

logger = logging.getLogger('crypto-bot')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


import json
import os
import time


def append_equity(path: str, cycle: int, equity: float, pnl: float, positions: dict) -> None:
    """Adiciona um registro de ciclo ao arquivo JSON (cria se não existir)."""
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    history = load_history(path)
    record = {
        'cycle': cycle,
        'ts': int(time.time()),
        'equity': round(equity, 2),
        'pnl': round(pnl, 2),
        'positions': positions,
    }
    history.append(record)
    with open(path, 'w') as f:
        json.dump(history, f, indent=2)


def load_history(path: str) -> list[dict]:
    """Carrega o histórico; retorna [] se não existir ou estiver corrompido."""
    logger.info('load_history path=%s', path)
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        # arquivo corrompido: recomeça limpo
        return []


def latest_equity(path: str) -> float | None:
    """Retorna a última equity registrada ou None se vazio."""
    history = load_history(path)
    if not history:
        return None
    return history[-1].get('equity')
