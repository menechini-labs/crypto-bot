"""Carrega config.yaml (parser mínimo de YAML, sem dependências)."""
import os


def load_config(path: str = None) -> dict:
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    cfg: dict = {}
    section: dict | None = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.rstrip("\n")
            if not raw.strip() or raw.strip().startswith("#"):
                continue
            if raw.startswith(" ") or raw.startswith("\t"):
                # item de lista ou sub-chave
                item = raw.strip()
                if item.startswith("- "):
                    if isinstance(section, list):
                        section.append(_cast(item[2:].strip()))
                else:
                    if ":" in item:
                        k, v = item.split(":", 1)
                        if isinstance(section, dict):
                            section[k.strip()] = _cast(v.strip())
            else:
                if ":" in raw:
                    k, v = raw.split(":", 1)
                    key = k.strip()
                    val = v.strip()
                    if val == "":
                        # inicia seção
                        if key == "symbols":
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
    if "#" in v:
        v = v.split("#", 1)[0].strip()
    if v == "":
        return None
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        return v
