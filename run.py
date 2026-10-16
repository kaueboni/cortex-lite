"""Atalho para rodar sem instalar: python C:/caminho/cortex-lite/run.py <comando>"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cortexlite.cli import main  # noqa: E402

sys.exit(main())
