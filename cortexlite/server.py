"""Servidor MCP (stdio) do cortex-lite, sem dependências: só a biblioteca padrão.

O protocolo MCP sobre stdio é JSON-RPC 2.0, uma mensagem JSON por linha.
Este servidor implementa o necessário para ferramentas: initialize, ping,
tools/list e tools/call.

Rodar: python run.py serve
"""
from __future__ import annotations

import json
import sys
from typing import Any, Callable

from .store import GLOBAL, KINDS, Store, detect_project

SERVER_NAME = "cortex-lite"
SERVER_VERSION = "0.3.1"
DEFAULT_PROTOCOL = "2025-06-18"

INSTRUCTIONS = f"""
Memória persistente entre sessões e entre agentes.
Cada memória pertence a um projeto (detectado pelo repositório git) ou é global.
Regra geral: quem decide grava, quem executa consulta.

Quando usar:
- Antes de planejar, revisar ou pesquisar: `recall` com 2-6 palavras-chave do assunto.
- Ao fechar uma decisão, lição, achado de pesquisa ou pendência que valha para sessões futuras:
  `memory_save` com kind em {", ".join(KINDS)}.
- Se uma decisão nova invalida uma antiga: `memory_save` com `supersedes=[id_antigo]`.
  A antiga é mantida no histórico, mas deixa de ser lembrada como vigente.

Não salve: código, conteúdo de specs (ficam em markdown no repositório), segredos, credenciais,
dados de clientes, nem o que for trivialmente redescoberto lendo o código.
Uma memória = um fato autocontido, escrito para quem não viu a conversa.
""".strip()


def _project(args: dict, global_scope: bool = False) -> str:
    if global_scope:
        return GLOBAL
    return args.get("project") or detect_project()


# ------------------------------------------------------------- ferramentas
def memory_save(s: Store, a: dict) -> dict:
    try:
        mem = s.save(
            a["content"],
            id=a.get("id") or None,
            title=a.get("title", ""),
            kind=a.get("kind", "fato"),
            project=_project(a, bool(a.get("global_scope"))),
            agent=a.get("agent", ""),
            tags=a.get("tags"),
            supersedes=a.get("supersedes"),
        )
    except ValueError as e:
        return {"error": str(e)}
    return {"saved": mem.to_dict(full=False)}


def recall(s: Store, a: dict) -> dict:
    proj = _project(a)
    hits = s.recall(
        a["query"],
        project=proj,
        kind=a.get("kind") or None,
        agent=a.get("agent") or None,
        top_k=max(1, min(int(a.get("top_k", 5)), 20)),
        include_superseded=bool(a.get("include_superseded")),
    )
    return {"project": proj, "results": [m.to_dict(full=False) for m in hits]}


def memory_get(s: Store, a: dict) -> dict:
    return {"memories": [m.to_dict(full=True) for m in s.get(list(a["ids"]))]}


def memory_list(s: Store, a: dict) -> dict:
    proj = _project(a)
    mems = s.list(
        project=proj,
        kind=a.get("kind") or None,
        agent=a.get("agent") or None,
        limit=max(1, min(int(a.get("limit", 30)), 200)),
    )
    return {"project": proj, "memories": [m.to_dict(full=False) for m in mems]}


def memory_supersede(s: Store, a: dict) -> dict:
    return {"ok": s.supersede(a["old_id"], a.get("new_id") or None)}


def memory_delete(s: Store, a: dict) -> dict:
    return {"ok": s.delete(a["id"])}


_STR = {"type": "string"}
_PROJECT = {"type": "string", "description": "Sobrescreve o projeto detectado pelo repositório atual."}
_KIND = {"type": "string", "enum": list(KINDS)}

TOOLS: dict[str, tuple[Callable[[Store, dict], dict], str, dict]] = {
    "memory_save": (
        memory_save,
        "Salva uma memória durável. Reutilize um id existente para ATUALIZAR aquela memória em vez de "
        "criar outra; use supersedes para marcar memórias que esta torna obsoletas.",
        {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Fato autocontido (1-5 frases), com o porquê."},
                "kind": {**_KIND, "default": "fato"},
                "title": {"type": "string", "description": "Resumo de uma linha; ajuda muito na busca."},
                "agent": {"type": "string", "description": "Quem registrou: o nome ou papel do agente (livre)."},
                "tags": {"type": "array", "items": _STR},
                "id": {"type": "string", "description": "Id existente para atualizar aquela memória."},
                "supersedes": {"type": "array", "items": _STR, "description": "Ids que esta memória torna obsoletos."},
                "global_scope": {"type": "boolean", "description": "true = vale em todos os projetos."},
                "project": _PROJECT,
            },
            "required": ["content"],
        },
    ),
    "recall": (
        recall,
        "Busca memórias relevantes do projeto atual e as globais. Palavras-chave (nomes, siglas, termos "
        "técnicos) funcionam melhor que frases. Retorna prévias; memory_get traz o texto completo.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "kind": _KIND,
                "agent": _STR,
                "top_k": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
                "include_superseded": {"type": "boolean", "default": False},
                "project": _PROJECT,
            },
            "required": ["query"],
        },
    ),
    "memory_get": (
        memory_get,
        "Retorna o conteúdo completo das memórias pelos ids.",
        {"type": "object", "properties": {"ids": {"type": "array", "items": _STR}}, "required": ["ids"]},
    ),
    "memory_list": (
        memory_list,
        "Lista as memórias vigentes do projeto, mais recentes primeiro.",
        {
            "type": "object",
            "properties": {
                "kind": _KIND,
                "agent": _STR,
                "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 30},
                "project": _PROJECT,
            },
        },
    ),
    "memory_supersede": (
        memory_supersede,
        "Marca uma memória como obsoleta sem apagar. new_id: a que a substitui, se houver.",
        {
            "type": "object",
            "properties": {"old_id": _STR, "new_id": _STR},
            "required": ["old_id"],
        },
    ),
    "memory_delete": (
        memory_delete,
        "Apaga uma memória de vez. Só quando o usuário pedir explicitamente (algo salvo por engano ou "
        "sensível); para decisões revogadas, use memory_supersede.",
        {"type": "object", "properties": {"id": _STR}, "required": ["id"]},
    ),
}


# --------------------------------------------------------------- protocolo
def handle(msg: dict) -> dict | None:
    """Processa uma mensagem JSON-RPC e devolve a resposta (None para notificações)."""
    method = msg.get("method")
    msg_id = msg.get("id")
    if msg_id is None:
        return None  # notificação (ex.: notifications/initialized): não responde

    def ok(result: Any) -> dict:
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    def err(code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}

    params = msg.get("params") or {}
    if method == "initialize":
        return ok(
            {
                "protocolVersion": params.get("protocolVersion") or DEFAULT_PROTOCOL,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": INSTRUCTIONS,
            }
        )
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok(
            {"tools": [{"name": n, "description": d, "inputSchema": schema} for n, (_, d, schema) in TOOLS.items()]}
        )
    if method == "tools/call":
        name = params.get("name")
        if name not in TOOLS:
            return err(-32602, f"ferramenta desconhecida: {name}")
        fn = TOOLS[name][0]
        s = Store()
        try:
            result = fn(s, params.get("arguments") or {})
            is_error = "error" in result
        except KeyError as e:
            result, is_error = {"error": f"argumento obrigatório ausente: {e.args[0]}"}, True
        except Exception as e:  # noqa: BLE001
            result, is_error = {"error": f"{type(e).__name__}: {e}"}, True
        finally:
            s.close()
        text = json.dumps(result, ensure_ascii=False, indent=2)
        return ok({"content": [{"type": "text", "text": text}], "isError": is_error})
    return err(-32601, f"método não suportado: {method}")


def main() -> None:
    # Bytes + UTF-8 explícito: no Windows o modo texto trocaria \n por \r\n e usaria cp1252.
    out = sys.stdout.buffer
    for raw in sys.stdin.buffer:
        line = raw.strip()
        if not line:
            continue
        try:
            msg = json.loads(line.decode("utf-8"))
        except ValueError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "JSON inválido"}}
        else:
            batch = msg if isinstance(msg, list) else [msg]
            replies = [r for r in (handle(m) for m in batch if isinstance(m, dict)) if r is not None]
            if not replies:
                continue
            reply = replies if isinstance(msg, list) else replies[0]
        out.write(json.dumps(reply, ensure_ascii=False).encode("utf-8") + b"\n")
        out.flush()
