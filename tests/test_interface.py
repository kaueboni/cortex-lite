"""Contrato público do cortex-lite.

Integrações (por exemplo, plugins que montam subagentes) dependem destes nomes.
Se um teste daqui falhar, a mudança é incompatível: exige versão maior e nota de
migração no CHANGELOG.md.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cortexlite.server import INSTRUCTIONS, TOOLS, handle  # noqa: E402
from cortexlite.store import KINDS  # noqa: E402

PUBLIC_TOOLS = {"recall", "memory_get", "memory_list", "memory_save", "memory_supersede", "memory_delete"}
PUBLIC_KINDS = ("decisao", "licao", "achado", "fato", "preferencia", "pendencia")
PROFILES = ("leitor", "pesquisador", "decisor", "executor", "revisor")
SQUAD_ROLES = ("tech-lead", "developer", "auditor", "researcher", "discovery", "contract-tester")


def test_tool_names_are_stable():
    assert set(TOOLS) == PUBLIC_TOOLS
    listed = handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"]
    assert {t["name"] for t in listed} == PUBLIC_TOOLS


def test_server_name_is_stable():
    mcp = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    assert "memoria" in mcp["mcpServers"]


def test_kinds_are_stable():
    assert tuple(KINDS) == PUBLIC_KINDS


def test_profiles_documented_in_skill_and_readme():
    skill = (ROOT / "skills" / "memoria" / "SKILL.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for profile in PROFILES:
        assert f"**{profile}**" in skill, profile
        assert re.search(rf"^\| {profile} \|", readme, re.MULTILINE), profile


def test_no_coupling_to_a_specific_squad():
    skill = (ROOT / "skills" / "memoria" / "SKILL.md").read_text(encoding="utf-8")
    texts = {"INSTRUCTIONS": INSTRUCTIONS, "SKILL.md": skill}
    texts.update({f"tool:{n}": json.dumps(schema, ensure_ascii=False) for n, (_, _, schema) in TOOLS.items()})
    for where, text in texts.items():
        for role in SQUAD_ROLES:
            assert role not in text, f"{where} cita '{role}'"


def test_delete_is_described_as_human_only():
    _, description, _ = TOOLS["memory_delete"]
    assert "usuário pedir" in description
