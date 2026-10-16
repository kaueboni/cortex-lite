"""Regressões do Windows: concorrência na criação do banco e fim de linha do export."""
import multiprocessing as mp
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _open_and_save(args):
    db, n = args
    from cortexlite.store import Store

    errors = 0
    for i in range(2):
        try:
            s = Store(db)
            s.save(f"nota {n}-{i} concorrência", title=f"t{n}-{i}", project="conc")
            s.close()
        except Exception:  # noqa: BLE001
            errors += 1
    return errors


def test_concurrent_first_open_does_not_lock(tmp_path):
    ctx = mp.get_context("spawn")
    total = 0
    with ctx.Pool(8) as pool:
        for rodada in range(6):  # cada rodada cria um banco novo: é aí que a disputa acontece
            db = tmp_path / "pasta com espaço" / f"memoria{rodada}.db"
            total += sum(pool.map(_open_and_save, [(str(db), n) for n in range(8)]))
    assert total == 0


def test_export_uses_lf_and_utf8(tmp_path):
    env = dict(os.environ, CORTEXLITE_PATH=str(tmp_path / "m.db"))
    run = [sys.executable, str(ROOT / "run.py")]
    subprocess.run([*run, "save", "Decisão com acentuação ção", "--title", "Título"], env=env, check=True)
    out = subprocess.run([*run, "export"], env=env, check=True, capture_output=True).stdout
    assert b"\r\n" not in out
    assert "Decisão com acentuação ção".encode("utf-8") in out
