"""Servidor MCP (stdio) do cortex-lite.

Rodar: python -m cortexlite serve
"""
from __future__ import annotations

from contextlib import contextmanager

try:  # SDK mcp 2.x
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # SDK mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

from .store import GLOBAL, KINDS, Store, detect_project

INSTRUCTIONS = f"""
Memória persistente entre sessões e entre agentes (tech-lead, developer, auditor, researcher).
Cada memória pertence a um projeto (detectado pelo repositório git) ou é global.

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

mcp = _Server("cortex-lite", instructions=INSTRUCTIONS)


@contextmanager
def _store():
    # Uma conexão por chamada: o SDK pode executar ferramentas em threads diferentes.
    s = Store()
    try:
        yield s
    finally:
        s.close()


def _project(project: str | None, global_scope: bool = False) -> str:
    if global_scope:
        return GLOBAL
    return project or detect_project()


@mcp.tool()
def memory_save(
    content: str,
    kind: str = "fato",
    title: str = "",
    agent: str = "",
    tags: list[str] | None = None,
    id: str = "",
    supersedes: list[str] | None = None,
    global_scope: bool = False,
    project: str = "",
) -> dict:
    """Salva uma memória durável.

    content: o fato autocontido (1-5 frases), com o porquê quando houver.
    kind: decisao | licao | achado | fato | preferencia | pendencia.
    title: resumo de uma linha (ajuda muito na busca).
    agent: quem registrou (tech-lead, developer, auditor, researcher).
    id: reutilize um id existente para ATUALIZAR aquela memória em vez de criar outra.
    supersedes: ids que esta memória torna obsoletos (ficam no histórico, saem do recall).
    global_scope: true para algo que vale em todos os projetos (ex.: preferências pessoais).
    project: sobrescreve o projeto detectado pelo repositório atual.
    """
    with _store() as s:
        try:
            mem = s.save(
                content,
                id=id or None,
                title=title,
                kind=kind,
                project=_project(project, global_scope),
                agent=agent,
                tags=tags,
                supersedes=supersedes,
            )
        except ValueError as e:
            # Devolve o motivo ao modelo para ele corrigir a chamada.
            return {"error": str(e)}
        return {"saved": mem.to_dict(full=False)}


@mcp.tool()
def recall(
    query: str,
    kind: str = "",
    agent: str = "",
    top_k: int = 5,
    include_superseded: bool = False,
    project: str = "",
) -> dict:
    """Busca memórias relevantes do projeto atual e as globais.

    query: palavras-chave do assunto (nomes, siglas, termos técnicos funcionam melhor que frases).
    kind/agent: filtros opcionais. Retorna prévias; use memory_get para o texto completo.
    """
    with _store() as s:
        proj = _project(project)
        hits = s.recall(
            query,
            project=proj,
            kind=kind or None,
            agent=agent or None,
            top_k=max(1, min(top_k, 20)),
            include_superseded=include_superseded,
        )
        return {"project": proj, "results": [m.to_dict(full=False) for m in hits]}


@mcp.tool()
def memory_get(ids: list[str]) -> dict:
    """Retorna o conteúdo completo das memórias pelos ids."""
    with _store() as s:
        return {"memories": [m.to_dict(full=True) for m in s.get(ids)]}


@mcp.tool()
def memory_list(kind: str = "", agent: str = "", limit: int = 30, project: str = "") -> dict:
    """Lista as memórias vigentes do projeto, mais recentes primeiro."""
    with _store() as s:
        proj = _project(project)
        mems = s.list(project=proj, kind=kind or None, agent=agent or None, limit=max(1, min(limit, 200)))
        return {"project": proj, "memories": [m.to_dict(full=False) for m in mems]}


@mcp.tool()
def memory_supersede(old_id: str, new_id: str = "") -> dict:
    """Marca uma memória como obsoleta (sem apagar). new_id: a que a substitui, se houver."""
    with _store() as s:
        return {"ok": s.supersede(old_id, new_id or None)}


@mcp.tool()
def memory_delete(id: str) -> dict:
    """Apaga uma memória de vez. Use só quando o usuário pedir explicitamente
    (ex.: algo salvo por engano ou sensível); para decisões revogadas, use memory_supersede."""
    with _store() as s:
        return {"ok": s.delete(id)}


def main() -> None:
    mcp.run()
