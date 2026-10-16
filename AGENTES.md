# Integrando o cortex-lite a agentes e fluxos

O cortex-lite não conhece nenhum fluxo, squad ou agente específico. Ele publica três coisas, que são a
sua **interface estável** (veja [Interface estável](README.md#interface-estável)):

1. as **ferramentas** MCP, com o efeito de cada uma;
2. os **tipos de memória** (`kind`);
3. os **perfis de uso** abaixo.

Quem integra (você, um plugin de squad, um template de projeto) decide **qual agente usa qual perfil**.
A regra geral: **quem decide grava, quem executa consulta.**

## Ferramentas por efeito

| Ferramenta | Nome completo para listar num subagente | Efeito |
| --- | --- | --- |
| `recall` | `mcp__plugin_cortex-lite_memoria__recall` | leitura |
| `memory_get` | `mcp__plugin_cortex-lite_memoria__memory_get` | leitura |
| `memory_list` | `mcp__plugin_cortex-lite_memoria__memory_list` | leitura |
| `memory_save` | `mcp__plugin_cortex-lite_memoria__memory_save` | escrita |
| `memory_supersede` | `mcp__plugin_cortex-lite_memoria__memory_supersede` | escrita |
| `memory_delete` | `mcp__plugin_cortex-lite_memoria__memory_delete` | destrutiva: só humano, a pedido |

O nome completo segue o padrão do Claude Code para MCP de plugin:
`mcp__plugin_<plugin>_<servidor>__<ferramenta>`, com plugin `cortex-lite` e servidor `memoria`
(definido em `.mcp.json`).

## Perfis de uso

| Perfil | Ferramentas | O que grava |
| --- | --- | --- |
| leitor | `recall`, `memory_get`, `memory_list` | nada |
| pesquisador | + `memory_save` | `achado`, com fonte e data |
| decisor | + `memory_save`, `memory_supersede` | `decisao` e `pendencia` |
| executor | + `memory_save` | `licao` que vai se repetir |
| revisor | + `memory_save`, `memory_supersede` | `licao` de padrões recorrentes |

Nenhum perfil recebe `memory_delete`. A descrição completa de cada perfil está na skill
[`memoria`](skills/memoria/SKILL.md).

## Subagentes: o que muda

1. **Lista fixa de ferramentas.** Um subagente com o campo `tools:` só enxerga o que está listado.
   As ferramentas do cortex-lite precisam aparecer com o **nome completo** da tabela acima.
2. **Os hooks não alcançam subagentes.** O índice do `SessionStart` e o recall automático do
   `UserPromptSubmit` entram só no contexto da **sessão principal**: o pedido que o orquestrador
   passa a um subagente não é um prompt do usuário, e o subagente começa com contexto próprio. Por
   isso, subagentes devem fazer `recall` explicitamente.
3. **Pré-carregue a skill.** Liste a skill no cabeçalho do agente, em `skills:` (lista YAML), com o
   nome do plugin: `cortex-lite:memoria`. Isso é mais confiável do que pedir no texto.

### Exemplo: subagente com perfil leitor

```markdown
---
name: meu-agente-leitor
description: 'Mapeia o projeto antes de uma mudança. Use proactively no início de cada feature.'
tools: Read, Grep, Glob, mcp__plugin_cortex-lite_memoria__recall, mcp__plugin_cortex-lite_memoria__memory_get, mcp__plugin_cortex-lite_memoria__memory_list
skills:
  - cortex-lite:memoria
---
Antes de ler o código, faça recall do assunto. Siga o perfil **leitor** da skill memoria:
consulte, não grave.
```

### Exemplo: subagente com perfil decisor

```markdown
---
name: meu-agente-decisor
description: 'Escreve specs e planos. Use para especificar uma feature.'
tools: Read, Grep, Glob, Write, Edit, mcp__plugin_cortex-lite_memoria__recall, mcp__plugin_cortex-lite_memoria__memory_get, mcp__plugin_cortex-lite_memoria__memory_list, mcp__plugin_cortex-lite_memoria__memory_save, mcp__plugin_cortex-lite_memoria__memory_supersede
skills:
  - cortex-lite:memoria
---
Siga o perfil **decisor** da skill memoria: grave decisões que outras partes do projeto devem
respeitar e, ao fim do planejamento, as pendências.
```

Use aspas simples na `description` se ela tiver `:` seguido de espaço; sem isso, o YAML do
cabeçalho fica inválido e o agente não carrega.

## Revisão humana

De tempos em tempos, ou ao fim de cada feature, exporte a memória do projeto e versione o markdown
(o projeto é detectado pelo repositório git da pasta atual):

```
py <pasta do cortex-lite>/run.py export > docs/MEMORIA.md        # Windows
python3 <pasta do cortex-lite>/run.py export > docs/MEMORIA.md   # macOS / Linux
```

Se algo estiver errado, corrija com `memory_save` usando o mesmo `id`, ou marque como substituído.

## Exemplo de mapeamento (ilustrativo)

Uma squad SDD com seis agentes poderia mapear assim; o mapeamento é dela, não do cortex-lite:

| Agente da squad | Perfil |
| --- | --- |
| discovery, contract-tester | leitor |
| researcher | pesquisador |
| tech-lead | decisor |
| developer | executor |
| auditor | revisor |

O plugin [minimal-squad](https://github.com/kaueboni/minimal-squad) aplica um mapeamento como esse
automaticamente quando detecta o cortex-lite.
