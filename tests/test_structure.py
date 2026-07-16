"""TDD: valida a estrutura em pacotes (core/).

Este teste DEVE falhar antes da reorganizacao (core/ nao existe ainda).
Apos mover os modulos para core/ e ajustar sys.path, todos os imports
devem funcionar a partir da raiz do projeto.

Regras:
- core/ deve conter todos os modulos de dominio.
- cli.py na raiz deve conseguir importar de core.
- tests/ deve conseguir importar de core.
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(ROOT, "core")

# garante que core/ esta no path (como cli.py e tests fazem)
if CORE not in sys.path:
    sys.path.insert(0, CORE)


class TestStructure(unittest.TestCase):
    def test_core_dir_exists(self):
        self.assertTrue(os.path.isdir(CORE), "core/ deve existir")

    def test_core_modules_importable(self):
        # lista de modulos esperados em core/
        expected = [
            "config_loader",
            "market",
            "indicators",
            "strategy",
            "wallet",
            "risk",
            "execution",
            "backtest",
            "reporter",
            "synth",
        ]
        for mod in expected:
            with self.subTest(module=mod):
                __import__(mod)

    def test_cli_imports_core(self):
        # cli.py na raiz deve importar de core sem erro
        ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        import cli  # noqa: F401


if __name__ == "__main__":
    unittest.main()
