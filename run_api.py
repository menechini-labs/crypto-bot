#!/usr/bin/env python3
"""Serve Strategy API via Uvicorn."""

import subprocess
import sys

if __name__ == '__main__':
    subprocess.run(
        [
            sys.executable,
            '-m',
            'uvicorn',
            'core.strategy_api:app',
            '--host',
            '0.0.0.0',
            '--port',
            '8000',
        ],
        check=True,
    )
