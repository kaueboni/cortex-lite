"""Armazenamento de memórias: um arquivo SQLite com busca full-text (FTS5/BM25).

Só usa a biblioteca padrão do Python, para que os hooks iniciem rápido e
rodem em qualquer máquina que tenha Python 3.10+.
"""
from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

GLOBAL = "*"  # projeto especial: memória válida em todos os projetos
KINDS = ("decisao", "licao", "achado", "fato", "preferencia", "pendencia")

# Palavras que não ajudam a achar nada (pt + en). Comparadas sem acento.
STOPWORDS = set(
    """
    a o as os um uma uns umas de do da dos das no na nos nas em por para pra pro
    com sem sob sobre entre ate e ou mas que se nao sim ja tambem como quando onde
    qual quais quem isso isto esse essa este esta aquele aquela ele ela eles elas
    eu voce voces nos meu minha seu sua nosso nossa ao aos ser estar ter tem foi
    era sao esta estao vai vou faz fazer pode posso precisa preciso agora entao
    aqui ali la mais menos muito pouco bem ok okay beleza blz segue seguir continua
    continue vamos bora pode favor obrigado valeu certo tipo coisa coisas
    the an of to in on at for from with without by is are was were be been it its
    this that these those and or but not yes no do does did can could should would
    will just please thanks go ahead lets let me my you your we our what which who
    how why when where there here then than so also very
    """.split()
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fold(text: str) -> str:
    """Minúsculas e sem acento: 'Decisão' -> 'decisao'."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_project(name: str) -> str:
    """'Radar-Consumidor' e 'radar_consumidor' viram o mesmo projeto."""
    if name == GLOBAL:
        return GLOBAL
    return re.sub(r"[^a-z0-9]", "", fold(name)) or "default"


def detect_project(cwd: str | os.PathLike | None = None) -> str:
    """Nome do repositório git que contém cwd; senão, o nome da pasta."""
    env = os.environ.get("CORTEXLITE_PROJECT")
    if env:
        return normalize_project(env)
    path = Path(cwd or os.getcwd()).resolve()
    for p in (path, *path.parents):
        if (p / ".git").exists():
            return normalize_project(p.name)
    return normalize_project(path.name)


def query_terms(query: str) -> list[str]:
    """Termos úteis da consulta, sem acento, sem stopwords, sem repetição."""
    seen: list[str] = []
    for tok in re.findall(r"\w+", fold(query)):
        if len(tok) < 2 or tok in STOPWORDS or tok in seen:
            continue
        seen.append(tok)
    return seen[:24]


def stem(term: str) -> str:
    """Radical para busca por prefixo, cobrindo plural e flexões do português:
    'listagem' casa 'listagens', 'reclamacoes' casa 'reclamacao'."""
    if len(term) <= 6:
        return term
    return term[:6] if len(term) <= 8 else term[:7]


def default_db_path() -> Path:
    env = os.environ.get("CORTEXLITE_PATH")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".cortexlite" / "memoria.db"


@dataclass
class Memory:
    id: str
    content: str
    title: str
    kind: str
    project: str
    agent: str
    tags: str
    status: str
    superseded_by: str | None
    created_at: str
    updated_at: str
    score: float = 0.0
    coverage: float = 0.0
    matched: list[str] = field(default_factory=list)

    def headline(self) -> str:
        return self.title or self.content.strip().splitlines()[0][:100]

    def to_dict(self, full: bool = True) -> dict:
        d = {
            "id": self.id,
            "title": self.headline(),
            "kind": self.kind,
            "project": self.project,
            "agent": self.agent,
            "tags": self.tags,
            "status": self.status,
            "updated_at": self.updated_at,
        }
        if self.superseded_by:
            d["superseded_by"] = self.superseded_by
        if full:
            d["content"] = self.content
        else:
            d["preview"] = _preview(self.content, 280)
        if self.coverage:
            d["coverage"] = round(self.coverage, 2)
        return d


def _preview(text: str, limit: int) -> str:
    one = " ".join(text.split())
    return one if len(one) <= limit else one[: limit - 1].rstrip() + "…"


def _slug(text: str) -> str:
    words = re.findall(r"[a-z0-9]+", fold(text))
    words = [w for w in words if w not in STOPWORDS][:6] or ["memoria"]
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:6]
    return "-".join(words)[:48] + "-" + digest


SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    rid           INTEGER PRIMARY KEY,
    id            TEXT NOT NULL UNIQUE,
    content       TEXT NOT NULL,
    title         TEXT NOT NULL DEFAULT '',
    kind          TEXT NOT NULL DEFAULT 'fato',
    project       TEXT NOT NULL,
    agent         TEXT NOT NULL DEFAULT '',
    tags          TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL DEFAULT 'active',
    superseded_by TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS memories_project ON memories(project, status, updated_at);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    title, content, tags,
    content='memories', content_rowid='rid',
    tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, title, content, tags)
    VALUES (new.rid, new.title, new.content, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, title, content, tags)
    VALUES ('delete', old.rid, old.title, old.content, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, title, content, tags)
    VALUES ('delete', old.rid, old.title, old.content, old.tags);
    INSERT INTO memories_fts(rowid, title, content, tags)
    VALUES (new.rid, new.title, new.content, new.tags);
END;
"""

COLUMNS = "id, content, title, kind, project, agent, tags, status, superseded_by, created_at, updated_at"


class Store:
    def __init__(self, path: str | os.PathLike | None = None):
        self.path = Path(path) if path else default_db_path()
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path), timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA busy_timeout=5000")
        self._init_schema()

    def _init_schema(self) -> None:
        # WAL: várias sessões do Claude Code podem usar o mesmo arquivo ao mesmo tempo.
        # Na criação do banco, vários processos disputam a troca de modo; no Windows isso
        # chega a lançar "database is locked" mesmo com timeout, então repete a tentativa.
        for attempt in range(10):
            try:
                self.db.execute("PRAGMA journal_mode=WAL")
                self.db.executescript(SCHEMA)
                return
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc) or attempt == 9:
                    raise
                time.sleep(0.05 * (attempt + 1))

    def close(self) -> None:
        self.db.close()

    # ---------------------------------------------------------------- escrita
    def save(
        self,
        content: str,
        *,
        id: str | None = None,
        title: str = "",
        kind: str = "fato",
        project: str | None = None,
        agent: str = "",
        tags: list[str] | str | None = None,
        supersedes: list[str] | None = None,
    ) -> Memory:
        content = (content or "").strip()
        if not content:
            raise ValueError("content vazio")
        kind = fold(kind or "fato")
        if kind not in KINDS:
            raise ValueError(f"kind inválido: {kind!r}; use um de {', '.join(KINDS)}")
        project = normalize_project(project) if project else detect_project()
        tag_text = " ".join(tags) if isinstance(tags, list) else (tags or "")
        mem_id = (id or "").strip() or _slug(title or content)
        now = _now()
        with self.db:
            existing = self.db.execute("SELECT created_at FROM memories WHERE id=?", (mem_id,)).fetchone()
            if existing:
                # Mesmo id = nova versão do mesmo fato: substitui, não duplica.
                self.db.execute(
                    """UPDATE memories SET content=?, title=?, kind=?, project=?, agent=?, tags=?,
                       status='active', superseded_by=NULL, updated_at=? WHERE id=?""",
                    (content, title, kind, project, agent, tag_text, now, mem_id),
                )
            else:
                self.db.execute(
                    f"INSERT INTO memories ({COLUMNS}) VALUES (?,?,?,?,?,?,?,'active',NULL,?,?)",
                    (mem_id, content, title, kind, project, agent, tag_text, now, now),
                )
            for old in supersedes or []:
                if old != mem_id:
                    self.db.execute(
                        "UPDATE memories SET status='superseded', superseded_by=?, updated_at=? WHERE id=?",
                        (mem_id, now, old),
                    )
        return self.get([mem_id])[0]

    def supersede(self, old_id: str, new_id: str | None = None) -> bool:
        with self.db:
            cur = self.db.execute(
                "UPDATE memories SET status='superseded', superseded_by=?, updated_at=? WHERE id=?",
                (new_id, _now(), old_id),
            )
        return cur.rowcount > 0

    def delete(self, mem_id: str) -> bool:
        with self.db:
            cur = self.db.execute("DELETE FROM memories WHERE id=?", (mem_id,))
        return cur.rowcount > 0

    # ---------------------------------------------------------------- leitura
    def get(self, ids: list[str]) -> list[Memory]:
        if not ids:
            return []
        marks = ",".join("?" * len(ids))
        rows = self.db.execute(f"SELECT {COLUMNS} FROM memories WHERE id IN ({marks})", ids).fetchall()
        by_id = {r["id"]: Memory(**dict(r)) for r in rows}
        return [by_id[i] for i in ids if i in by_id]

    def list(
        self,
        *,
        project: str | None = None,
        kind: str | None = None,
        agent: str | None = None,
        include_global: bool = True,
        include_superseded: bool = False,
        limit: int = 30,
    ) -> list[Memory]:
        where, args = self._filters(project, kind, agent, include_global, include_superseded)
        sql = f"SELECT {COLUMNS} FROM memories m WHERE {where} ORDER BY updated_at DESC LIMIT ?"
        return [Memory(**dict(r)) for r in self.db.execute(sql, [*args, limit]).fetchall()]

    def recall(
        self,
        query: str,
        *,
        project: str | None = None,
        kind: str | None = None,
        agent: str | None = None,
        include_global: bool = True,
        include_superseded: bool = False,
        top_k: int = 5,
        min_coverage: float = 0.0,
    ) -> list[Memory]:
        """Busca por palavra-chave com BM25.

        Ordena primeiro pela fração dos termos da consulta que a memória contém
        (coverage) e depois pelo BM25. Assim uma memória que cita exatamente o
        termo pedido vence cinco memórias vagamente parecidas.
        """
        terms = query_terms(query)
        if not terms:
            return []
        # Termos curtos (siglas como "HA") só casam inteiros; os longos casam por prefixo.
        match = " OR ".join(f'"{stem(t)}"*' if len(t) >= 4 else f'"{t}"' for t in terms)
        where, args = self._filters(project, kind, agent, include_global, include_superseded)
        sql = f"""
            SELECT {", ".join("m." + c.strip() for c in COLUMNS.split(","))},
                   bm25(memories_fts, 3.0, 1.0, 2.0) AS rank
            FROM memories_fts JOIN memories m ON m.rid = memories_fts.rowid
            WHERE memories_fts MATCH ? AND {where}
            ORDER BY rank LIMIT ?
        """
        rows = self.db.execute(sql, [match, *args, max(top_k * 8, 40)]).fetchall()
        results: list[Memory] = []
        for r in rows:
            d = dict(r)
            rank = d.pop("rank")
            mem = Memory(**d, score=-rank)
            words = set(re.findall(r"\w+", fold(f"{mem.title} {mem.content} {mem.tags} {mem.kind}")))
            mem.matched = [
                t for t in terms if (t in words if len(t) < 4 else any(w.startswith(stem(t)) for w in words))
            ]
            mem.coverage = len(mem.matched) / len(terms)
            if mem.coverage >= min_coverage:
                results.append(mem)
        results.sort(key=lambda m: (m.coverage, m.score), reverse=True)
        return results[:top_k]

    def stats(self) -> dict:
        rows = self.db.execute(
            "SELECT project, status, COUNT(*) n FROM memories GROUP BY project, status ORDER BY project"
        ).fetchall()
        return {
            "path": str(self.path),
            "total": sum(r["n"] for r in rows),
            "by_project": [dict(r) for r in rows],
        }

    @staticmethod
    def _filters(project, kind, agent, include_global, include_superseded):
        where, args = ["1=1"], []
        if project != GLOBAL:
            proj = normalize_project(project) if project else detect_project()
            if include_global:
                where.append("m.project IN (?, ?)")
                args += [proj, GLOBAL]
            else:
                where.append("m.project = ?")
                args.append(proj)
        else:
            where.append("m.project = ?")
            args.append(GLOBAL)
        if kind:
            where.append("m.kind = ?")
            args.append(fold(kind))
        if agent:
            where.append("m.agent = ?")
            args.append(agent)
        if not include_superseded:
            where.append("m.status = 'active'")
        return " AND ".join(where), args
