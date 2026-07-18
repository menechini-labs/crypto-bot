"""Graphiti Memory Adapter — persistência de memória de longo prazo.

Armazena reflexões e trades em `/dev/shm/graphiti/` (RAM disk, volátil).
Quando disponível, usa memória compartilhada entre processos.
Fallback: diretório `data/memory/`.

Nenhuma dependência externa. Stdlib apenas.
"""

from __future__ import annotations

import json
import logging
import os
import time

log = logging.getLogger(__name__)

# Tenta usar RAM disk (Graphiti-style). Fallback para data/memory.
_GRAPHITI_BASE = '/dev/shm/graphiti'
_MEMORY_DIR = (
    _GRAPHITI_BASE
    if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK)
    else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data',
        'memory',
    )
)

os.makedirs(_MEMORY_DIR, exist_ok=True)


def _path(key: str) -> str:
    """Retorna path completo para uma chave de memória."""
    safe = key.replace('/', '_').replace(' ', '_').lower()
    return os.path.join(_MEMORY_DIR, f'{safe}.json')


def store(key: str, data: dict | list, ttl_hours: int = 72) -> None:
    """Armazena dados na memória de longo prazo com TTL.

    Args:
        key: chave para recuperação (ex: 'reflection_btc')
        data: dict ou list para persistir
        ttl_hours: horas antes de expirar (default 72h)
    """
    payload = {
        'ts': time.time(),
        'expires_at': time.time() + ttl_hours * 3600,
        'key': key,
        'data': data,
    }
    try:
        with open(_path(key), 'w', encoding='utf-8') as f:
            json.dump(payload, f)
        log.debug('memory_adapter stored key=%s ttl=%dh', key, ttl_hours)
    except OSError as e:
        log.warning('memory_adapter store failed key=%s: %s', key, e)


def load(key: str) -> dict | list | None:
    """Recupera dados da memória, respeitando TTL.

    Returns None se expirado ou inexistente.
    """
    fp = _path(key)
    import contextlib

    if not os.path.isfile(fp):
        return None
    try:
        with open(fp, encoding='utf-8') as f:
            payload = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    if payload.get('expires_at', 0) < time.time():
        with contextlib.suppress(OSError):
            os.remove(fp)
        return None
    return payload.get('data')


def load_reflections(symbol: str = '*') -> list[dict]:
    """Carrega reflexões recentes, opcionalmente filtradas por symbol."""
    _ = _path(f'reflection_{symbol}').replace('*', '') if symbol == '*' else None  # compat

    results: list[dict] = []
    try:
        for fname in os.listdir(_MEMORY_DIR):
            if not fname.startswith('reflection_'):
                continue
            fp = os.path.join(_MEMORY_DIR, fname)
            try:
                with open(fp, encoding='utf-8') as f:
                    payload = json.load(f)
                if payload.get('expires_at', 0) < time.time():
                    os.remove(fp)
                    continue
                entry = payload.get('data', {})
                if isinstance(entry, dict):
                    entry['_source'] = fname
                    results.append(entry)
            except (json.JSONDecodeError, OSError):
                continue
    except OSError:
        pass

    results.sort(key=lambda x: x.get('ts', 0), reverse=True)
    return results


def clear_expired() -> int:
    """Remove entradas expiradas. Retorna contagem."""
    count = 0
    try:
        for fname in os.listdir(_MEMORY_DIR):
            fp = os.path.join(_MEMORY_DIR, fname)
            try:
                with open(fp, encoding='utf-8') as f:
                    payload = json.load(f)
                if payload.get('expires_at', 0) < time.time():
                    os.remove(fp)
                    count += 1
            except (json.JSONDecodeError, OSError):
                continue
    except OSError:
        pass
    return count


def is_available() -> bool:
    """Verifica se o Graphiti RAM disk está acessível."""
    base = '/dev/shm/graphiti'
    return os.path.isdir('/dev/shm') and (
        os.path.isdir(base) or os.access('/dev/shm', os.W_OK)
    )
