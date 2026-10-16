import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cortexlite.store import GLOBAL, Store, detect_project, normalize_project, query_terms  # noqa: E402


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("CORTEXLITE_PATH", str(tmp_path / "m.db"))
    s = Store()
    yield s
    s.close()


def test_query_terms_drop_stopwords_and_accents():
    assert query_terms("Por que escolhemos o FastAPI?") == ["escolhemos", "fastapi"]
    assert query_terms("ok, pode seguir") == []
    assert query_terms("Decisão de autenticação") == ["decisao", "autenticacao"]


def test_normalize_project():
    assert normalize_project("Radar-Consumidor") == normalize_project("radar_consumidor") == "radarconsumidor"
    assert normalize_project(GLOBAL) == GLOBAL


def test_detect_project_uses_git_root(tmp_path, monkeypatch):
    monkeypatch.delenv("CORTEXLITE_PROJECT", raising=False)
    (tmp_path / "Meu-Repo" / ".git").mkdir(parents=True)
    sub = tmp_path / "Meu-Repo" / "src" / "api"
    sub.mkdir(parents=True)
    assert detect_project(sub) == "meurepo"


def test_save_and_recall_accent_insensitive(store):
    store.save("Escolhemos autenticação via OAuth2 com PKCE.", kind="decisao", project="p")
    hits = store.recall("autenticacao oauth", project="p")
    assert len(hits) == 1 and hits[0].coverage == 1.0


def test_exact_term_beats_vague_matches(store):
    for i in range(5):
        store.save(f"Notas gerais sobre cluster e disponibilidade, item {i}.", project="p")
    store.save("HA exige 3 nós no cluster.", project="p", id="ha")
    hits = store.recall("HA", project="p")
    assert hits[0].id == "ha"
    # sigla curta não casa por prefixo ("ha" não pega "habilitar")
    store.save("Habilitar logs de auditoria.", project="p", id="logs")
    assert [m.id for m in store.recall("HA", project="p")] == ["ha"]


def test_same_id_updates_instead_of_duplicating(store):
    store.save("Versão 1", id="x", project="p")
    store.save("Versão 2", id="x", project="p")
    mems = store.list(project="p")
    assert len(mems) == 1 and mems[0].content == "Versão 2"
    assert store.recall("versao", project="p")[0].content == "Versão 2"


def test_supersede_hides_from_recall_but_keeps_history(store):
    old = store.save("Banco: MySQL", kind="decisao", project="p", id="db-v1")
    store.save("Banco: Postgres (substitui MySQL)", kind="decisao", project="p", id="db-v2", supersedes=[old.id])
    assert [m.id for m in store.recall("banco", project="p")] == ["db-v2"]
    all_hits = store.recall("banco", project="p", include_superseded=True)
    assert {m.id for m in all_hits} == {"db-v1", "db-v2"}
    assert store.get(["db-v1"])[0].superseded_by == "db-v2"


def test_project_isolation_and_global(store):
    store.save("Segredo do projeto A: usa Kafka", project="a")
    store.save("Kaue prefere respostas curtas e diretas", project=GLOBAL, kind="preferencia")
    assert store.recall("kafka", project="b") == []
    assert len(store.recall("respostas curtas", project="b")) == 1
    assert len(store.recall("respostas curtas", project="b", include_global=False)) == 0


def test_invalid_kind_rejected(store):
    with pytest.raises(ValueError):
        store.save("x", kind="qualquer", project="p")


def _hook(event, payload, env):
    r = subprocess.run(
        [sys.executable, str(ROOT / "run.py"), "hook", event],
        input=json.dumps(payload).encode(),
        capture_output=True,
        env=env,
        timeout=20,
    )
    assert r.returncode == 0, r.stderr.decode()
    out = r.stdout.decode("utf-8").strip()
    return json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else ""


def test_hooks_end_to_end(tmp_path):
    env = {**os.environ, "CORTEXLITE_PATH": str(tmp_path / "h.db"), "CORTEXLITE_PROJECT": "radar"}
    run = lambda *a: subprocess.run([sys.executable, str(ROOT / "run.py"), *a], env=env, check=True, capture_output=True)  # noqa: E731
    run("save", "Usamos FastAPI pelo suporte async e OpenAPI.", "--kind", "decisao", "--title", "Framework web: FastAPI", "--agent", "tech-lead")
    run("save", "Rate limit da API do Consumidor.gov é 60 req/min.", "--kind", "achado", "--agent", "researcher")

    start = _hook("session-start", {"cwd": str(tmp_path)}, env)
    assert "2 itens" in start and "tech-lead" in start

    ctx = _hook("recall", {"prompt": "qual o rate limit da api do consumidor?", "cwd": str(tmp_path)}, env)
    assert "60 req/min" in ctx and "FastAPI" not in ctx

    assert _hook("recall", {"prompt": "ok, pode seguir", "cwd": str(tmp_path)}, env) == ""
    assert _hook("recall", {"prompt": "refatorar o frontend em react", "cwd": str(tmp_path)}, env) == ""


def test_hook_never_fails_on_garbage(tmp_path):
    env = {**os.environ, "CORTEXLITE_PATH": str(tmp_path / "g.db")}
    r = subprocess.run([sys.executable, str(ROOT / "run.py"), "hook", "recall"], input=b"not json", capture_output=True, env=env)
    assert r.returncode == 0 and r.stdout == b""


def test_export_markdown(tmp_path):
    env = {**os.environ, "CORTEXLITE_PATH": str(tmp_path / "e.db"), "CORTEXLITE_PROJECT": "radar"}
    run = lambda *a: subprocess.run([sys.executable, str(ROOT / "run.py"), *a], env=env, check=True, capture_output=True)  # noqa: E731
    run("save", "Banco: MySQL", "--kind", "decisao", "--id", "db-v1")
    run("save", "Banco: Postgres", "--kind", "decisao", "--id", "db-v2", "--supersedes", "db-v1")
    md = run("export").stdout.decode("utf-8")
    assert "## Decisao" in md and "substituída por db-v2" in md


def test_portuguese_plural_and_inflection(store):
    store.save("Exigir paginação em listagens de reclamações.", project="p", id="pag")
    assert store.recall("listagem", project="p")[0].id == "pag"
    assert store.recall("reclamacao", project="p")[0].id == "pag"
