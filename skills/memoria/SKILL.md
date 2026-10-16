---
name: memoria
description: Como usar a memória persistente do cortex-lite (ferramentas recall, memory_save, memory_get, memory_list, memory_supersede). Use ao planejar, especificar, implementar, revisar ou pesquisar num projeto, ao tomar ou revogar uma decisão de arquitetura, ao descobrir uma lição que vai se repetir, ao concluir uma pesquisa, ou quando o usuário pedir para lembrar, anotar, esquecer ou consultar o que já foi decidido.
---

# Memória do projeto (cortex-lite)

A memória guarda o **porquê** entre sessões e entre agentes: decisões, lições, achados de pesquisa,
pendências e preferências. Specs, planos, tarefas e código continuam nos arquivos do repositório.

Regra geral: **quem decide grava, quem executa consulta.**

## Antes de agir

- Na sessão principal, o início da sessão traz um índice das memórias vigentes do projeto. Leia com
  `memory_get` só as que importam para a tarefa.
- **Se você é um subagente, esse índice não chega até você.** Comece com `recall`.
- Antes de propor, revisar ou pesquisar, faça `recall` com 2 a 6 palavras-chave do assunto (nomes,
  siglas, termos técnicos). Se uma memória vigente contradiz o que você ia propor, siga a memória ou
  diga explicitamente que propõe substituí-la.

## O que gravar e com qual `kind`

| kind | Quando | Exemplo |
| --- | --- | --- |
| `decisao` | Escolha que outras features precisam respeitar | "Banco: Postgres + pgvector, pela busca semântica; SQLite descartado por concorrência." |
| `licao` | Algo que deu errado e pode voltar | "Testes de integração do repositório precisam de rollback, senão vazam dados." |
| `achado` | Resultado de pesquisa reutilizável, com fonte e data | "API X limita 60 req/min (docs oficiais, out/2026)." |
| `pendencia` | Questão em aberto que precisa de dono | "Definir retenção de logs (LGPD)." |
| `preferencia` | Gosto do usuário (geralmente `global_scope=true`) | "Prefere respostas curtas, em português." |
| `fato` | Informação estável do contexto | "Deploy só via pipeline; sem acesso direto à produção." |

Regras de escrita:
- Uma memória = um fato autocontido, legível por quem não viu a conversa. Sempre com `title`.
- Inclua o porquê e, em decisões, do que se abriu mão.
- Preencha `agent` com o nome ou papel de quem está gravando (texto livre).
- Para corrigir uma memória, salve de novo com o mesmo `id`. Para revogar uma decisão, salve a nova
  com `supersedes=["<id antigo>"]`. Não apague o histórico.
- `memory_delete` só quando o usuário pedir, por exemplo para algo salvo por engano ou sensível.

## Nunca gravar

Segredos, tokens, senhas, dados de clientes ou pessoais, código, conteúdo de specs e o que se
redescobre lendo o código em segundos.

## Perfis de uso

Cada agente segue o perfil que o fluxo dele atribuiu. Sem perfil definido, aja como **leitor** e só
grave quando o usuário pedir.

- **leitor** — consulta (`recall`, `memory_get`, `memory_list`). Não grava; se notar algo que
  mereça memória, diga no seu retorno.
- **pesquisador** — consulta achados antes de pesquisar e reaproveita os recentes, citando a data.
  Grava cada achado reutilizável (`achado`) com fonte e data; para temas que mudam rápido, inclua
  "verificar após <data>". Achados que valem para qualquer projeto vão com `global_scope=true`.
- **decisor** — grava decisões que outras partes do projeto devem respeitar (`decisao`, com o
  motivo e o que foi descartado) e as dúvidas em aberto (`pendencia`). Substitui decisões com
  `supersedes`/`memory_supersede`; nunca apaga. Decisões que valem só para uma feature ficam na
  spec dela, não na memória.
- **executor** — consulta o módulo e a tecnologia antes de implementar. Grava só lições que vão se
  repetir (`licao`); nunca progresso de tarefa.
- **revisor** — consulta decisões e lições ligadas ao que está revisando e confere se a mudança viola
  alguma. Grava padrões de problema recorrentes (`licao`), não casos pontuais; usa
  `memory_supersede` quando uma lição antiga não vale mais.
