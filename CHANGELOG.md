# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

**Interface pública** (integrações dependem dela): os nomes das ferramentas MCP
(`recall`, `memory_get`, `memory_list`, `memory_save`, `memory_supersede`, `memory_delete`),
o nome do servidor (`memoria`), os `kind` (`decisao`, `licao`, `achado`, `fato`, `preferencia`,
`pendencia`) e os perfis de uso (leitor, pesquisador, decisor, executor, revisor). Renomear ou
remover qualquer um deles é mudança incompatível: exige versão maior e uma nota de migração aqui.

## [0.3.0] - 2026-10-16

### Changed
- O cortex-lite deixa de citar papéis de uma squad específica. A skill `memoria`, o `AGENTES.md`, a
  descrição do servidor MCP e a do campo `agent` passam a ser genéricas.
- As orientações por papel viraram **perfis de uso**: leitor, pesquisador, decisor, executor e
  revisor. Quem integra decide qual agente usa qual perfil.

### Added
- Seção "Interface estável" no README, com a classificação das ferramentas por efeito e a tabela de
  perfis.
- Documentação para subagentes: nomes completos das ferramentas para o campo `tools:`, aviso de que
  os hooks só agem na sessão principal e exemplos de cabeçalho por perfil.
- Seções "O que vai onde" (incluindo a migração da memória automática do Claude Code), "Tokens:
  quando economiza" e "Time".
- Comandos equivalentes para macOS / Linux.
- Teste de contrato que trava os nomes das ferramentas, do servidor e dos `kind`.

## [0.2.0]

- Versão inicial publicada: servidor MCP, hooks `SessionStart` e `UserPromptSubmit`, skill
  `memoria`, CLI e export.
