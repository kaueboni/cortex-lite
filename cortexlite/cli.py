"""Linha de comando do cortex-lite: servidor MCP, hooks do Claude Code e utilidades.

  python -m cortexlite serve                 servidor MCP (stdio)
  python -m cortexlite hook session-start    hook SessionStart (lê JSON do stdin)
  python -m cortexlite hook recall           hook UserPromptSubmit (lê JSON do stdin)
  python -m cortexlite save "texto" --kind decisao --title "..."
  python -m cortexlite search "palavras"
  python -m cortexlite list
  python -m cortexlite export > MEMORIA.md   exporta para revisão em PR
  python -m cortexlite stats
  python -m cortexlite doctor
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .store import GLOBAL, KINDS, Store, detect_project, query_terms

VERSION = "0.1.0"


def _utf8_stdio() -> None:
    # No Windows o console padrão é cp1252; acentos quebrariam a saída dos hooks.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def _read_hook_input() -> dict:
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def _emit_context(event: str, text: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}, ensure_ascii=False))


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _disabled() -> bool:
    return os.environ.get("CORTEXLITE_DISABLE", "").lower() in ("1", "true", "yes", "sim")


# ------------------------------------------------------------------- hooks
def hook_session_start(data: dict) -> None:
    """Índice do que já se sabe sobre o projeto: uma linha por memória."""
    project = detect_project(data.get("cwd"))
    s = Store()
    try:
        mems = s.list(project=project, limit=_env_int("CORTEXLITE_SESSION_MAX", 20))
    finally:
        s.close()
    if not mems:
        return
    lines = [
        f"Memória do projeto '{project}' (cortex-lite): {len(mems)} itens vigentes, mais recentes primeiro.",
        "Use a ferramenta memory_get com os ids para ler o conteúdo completo quando for relevante.",
    ]
    for m in mems:
        scope = " [global]" if m.project == GLOBAL else ""
        who = f" ({m.agent})" if m.agent else ""
        lines.append(f"- {m.id} · {m.kind}{who} · {m.updated_at[:10]}{scope} · {m.headline()[:110]}")
    _emit_context("SessionStart", "\n".join(lines))


def _min_matches(n_terms: int) -> int:
    if n_terms <= 2:
        return 1
    if n_terms <= 6:
        return 2
    return 3


def hook_recall(data: dict) -> None:
    """Injeta só memórias que casam de verdade com o prompt, dentro de um orçamento de caracteres."""
    prompt = (data.get("prompt") or "").strip()
    if prompt.startswith("/"):
        prompt = prompt.split(maxsplit=1)[1] if " " in prompt else ""
    prompt = prompt[:1500]
    terms = query_terms(prompt)
    if not terms:
        return  # "ok", "segue", "pode ir": nada a buscar
    project = detect_project(data.get("cwd"))
    s = Store()
    try:
        hits = s.recall(prompt, project=project, top_k=_env_int("CORTEXLITE_RECALL_TOP_K", 4))
    finally:
        s.close()
    need = _min_matches(len(terms))
    hits = [m for m in hits if len(m.matched) >= need]
    if not hits:
        return
    budget = _env_int("CORTEXLITE_RECALL_BUDGET", 1200)
    lines = ["Memórias possivelmente relevantes (cortex-lite). Confira antes de seguir; memory_get traz o texto completo:"]
    used = len(lines[0])
    for m in hits:
        body = " ".join(m.content.split())
        line = f"- [{m.kind}] {m.id}: {body}"
        if len(line) > 320:
            line = line[:319].rstrip() + "…"
        if used + len(line) > budget:
            break
        lines.append(line)
        used += len(line)
    if len(lines) > 1:
        _emit_context("UserPromptSubmit", "\n".join(lines))


# --------------------------------------------------------------- comandos
def cmd_export(args) -> None:
    s = Store()
    try:
        project = GLOBAL if args.global_scope else (args.project or detect_project())
        mems = s.list(project=project, include_global=False, include_superseded=True, limit=10_000)
    finally:
        s.close()
    print(f"# Memória — {project}\n")
    print("<!-- Gerado por `python -m cortexlite export`. Revise em PR; o banco é a fonte. -->\n")
    for kind in KINDS:
        group = [m for m in mems if m.kind == kind]
        if not group:
            continue
        print(f"## {kind.capitalize()}\n")
        for m in sorted(group, key=lambda m: m.created_at):
            mark = "" if m.status == "active" else f" ~~(substituída por {m.superseded_by or '—'})~~"
            who = f" · {m.agent}" if m.agent else ""
            print(f"### {m.headline()}{mark}\n")
            print(f"`{m.id}` · {m.created_at[:10]}{who}\n")
            print(m.content.strip() + "\n")


def cmd_doctor(_args) -> int:
    import sqlite3

    ok = True

    def check(label, fn):
        nonlocal ok
        try:
            print(f"[ok]   {label}: {fn()}")
        except Exception as e:  # noqa: BLE001
            ok = False
            print(f"[FALHA] {label}: {e}")

    check("python", lambda: sys.version.split()[0] + ("" if sys.version_info >= (3, 10) else "  (precisa 3.10+)"))

    def fts():
        c = sqlite3.connect(":memory:")
        c.execute("CREATE VIRTUAL TABLE t USING fts5(x, tokenize='unicode61 remove_diacritics 2')")
        return f"FTS5 disponível (SQLite {sqlite3.sqlite_version})"

    check("sqlite", fts)

    def db():
        s = Store()
        st = s.stats()
        s.close()
        return f"{st['path']} ({st['total']} memórias)"

    check("banco", db)
    check("projeto detectado", lambda: detect_project())

    def sdk():
        from . import server  # noqa: F401

        return "SDK mcp importado, servidor pronto"

    check("mcp", sdk)
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    _utf8_stdio()
    p = argparse.ArgumentParser(prog="cortexlite", description="Memória persistente para agentes do Claude Code.")
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("serve", help="servidor MCP (stdio)")

    h = sub.add_parser("hook", help="hooks do Claude Code (leem JSON do stdin)")
    h.add_argument("event", choices=["session-start", "recall"])

    sv = sub.add_parser("save", help="salvar uma memória")
    sv.add_argument("content")
    sv.add_argument("--kind", default="fato", choices=KINDS)
    sv.add_argument("--title", default="")
    sv.add_argument("--agent", default="")
    sv.add_argument("--tags", default="")
    sv.add_argument("--id", default="")
    sv.add_argument("--supersedes", nargs="*", default=[])
    sv.add_argument("--project", default="")
    sv.add_argument("--global", dest="global_scope", action="store_true")

    se = sub.add_parser("search", help="buscar memórias")
    se.add_argument("query")
    se.add_argument("--top-k", type=int, default=5)
    se.add_argument("--project", default="")
    se.add_argument("--all", action="store_true", help="inclui substituídas")

    ls = sub.add_parser("list", help="listar memórias vigentes do projeto")
    ls.add_argument("--project", default="")
    ls.add_argument("--kind", default="")
    ls.add_argument("--limit", type=int, default=30)

    ex = sub.add_parser("export", help="exportar como markdown")
    ex.add_argument("--project", default="")
    ex.add_argument("--global", dest="global_scope", action="store_true")

    sub.add_parser("stats", help="contagem por projeto")
    sub.add_parser("doctor", help="verificar a instalação")

    args = p.parse_args(argv)

    if args.cmd == "serve":
        from .server import main as serve

        serve()
        return 0

    if args.cmd == "hook":
        # Um hook nunca pode travar ou quebrar o prompt: qualquer erro é silencioso.
        if _disabled():
            return 0
        try:
            data = _read_hook_input()
            (hook_session_start if args.event == "session-start" else hook_recall)(data)
        except Exception as e:  # noqa: BLE001
            if os.environ.get("CORTEXLITE_DEBUG"):
                print(f"cortex-lite hook erro: {e!r}", file=sys.stderr)
        return 0

    if args.cmd == "doctor":
        return cmd_doctor(args)
    if args.cmd == "export":
        cmd_export(args)
        return 0

    s = Store()
    try:
        if args.cmd == "save":
            mem = s.save(
                args.content,
                id=args.id or None,
                title=args.title,
                kind=args.kind,
                project=GLOBAL if args.global_scope else (args.project or None),
                agent=args.agent,
                tags=args.tags,
                supersedes=args.supersedes,
            )
            print(f"salva: {mem.id} (projeto {mem.project})")
        elif args.cmd == "search":
            hits = s.recall(args.query, project=args.project or None, top_k=args.top_k, include_superseded=args.all)
            if not hits:
                print("nada encontrado")
            for m in hits:
                flag = "" if m.status == "active" else " [substituída]"
                print(f"{m.coverage:.0%} · {m.id} · {m.kind}{flag}\n    {m.headline()}")
        elif args.cmd == "list":
            for m in s.list(project=args.project or None, kind=args.kind or None, limit=args.limit):
                print(f"{m.updated_at[:10]} · {m.id} · {m.kind} · {m.headline()[:90]}")
        elif args.cmd == "stats":
            print(json.dumps(s.stats(), ensure_ascii=False, indent=2))
    finally:
        s.close()
    return 0
