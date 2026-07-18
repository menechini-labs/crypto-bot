import logging
from typing import Any

logger = logging.getLogger('crypto-bot')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


"""Carrega config.yaml (parser mínimo de YAML, sem dependências)."""
import os


# AI-Trader integration config from env vars
AI_TRADER_ENABLED = os.environ.get("AI_TRADER_ENABLED", "").lower() in ("1", "true", "yes")
AI_TRADER_PUBLISH_CONFIDENCE = float(os.environ.get("AI_TRADER_PUBLISH_CONFIDENCE", "0.65"))


def load_config(path: str | None = None) -> dict[str, Any]:
    if path is None:
        # config.yaml fica na raiz do projeto (um nivel acima de core/)
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(root, 'config.yaml')
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    cfg: dict[str, Any] = {}
    section: dict[str, Any] | list[Any] | None = None
    with open(path, encoding='utf-8') as f:
        for line in f:
            raw = line.rstrip('\n')
            if not raw.strip() or raw.strip().startswith('#'):
                continue
            if raw.startswith(' ') or raw.startswith('\t'):
                # item de lista ou sub-chave
                item = raw.strip()
                if item.startswith('- '):
                    if isinstance(section, list):
                        section.append(_cast(item[2:].strip()))
                elif ':' in item:
                    k, v = item.split(':', 1)
                    if isinstance(section, dict):
                        section[k.strip()] = _cast(v.strip())
            elif ':' in raw:
                k, v = raw.split(':', 1)
                key = k.strip()
                val = v.strip()
                if val == '':
                    # inicia seção
                    if key == 'symbols':
                        section = []
                        cfg[key] = section
                    else:
                        section = {}
                        cfg[key] = section
                else:
                    cfg[key] = _cast(val)
                    section = None
    return cfg


def _cast(v: str):
    # remove comentário inline
    if '#' in v:
        v = v.split('#', 1)[0].strip()
    if v == '':
        return None
    if v.lower() in ('true', 'false'):
        return v.lower() == 'true'
    try:
        if '.' in v:
            return float(v)
        return int(v)
    except ValueError:
        return v
