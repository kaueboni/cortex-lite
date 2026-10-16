---
name: memoria
description: Como usar a memória persistente do cortex-lite (ferramentas recall, memory_save, memory_get, memory_supersede). Use ao planejar, especificar, implementar, revisar ou pesquisar num projeto, ao tomar ou revogar uma decisão de arquitetura, ao descobrir uma lição que vai se repetir, ao concluir uma pesquisa, ou quando o usuário pedir para lembrar, anotar, esquecer ou consultar o que já foi decidido.
---

# Memória do projeto (cortex-lite)

A memória guarda o **porquê** entre sessões e entre agentes: decisões, lições, achados de pesquisa,
pendências e preferências. Specs, planos, tasks e código continuam nos arquivos do repositório.

## Antes de agir

- O início da sessão traz um índice das memórias vigentes do projeto. Leia com `memory_get` só as
  que importam para a tarefa.
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
- Preencha `agent` com o papel que está gravando: `tech-lead`, `developer`, `auditor` ou `researcher`.
- Para corrigir uma memória, salve de novo com o mesmo `id`. Para revogar uma decisão, salve a nova
  com `supersedes=["<id antigo>"]`. Não apague o histórico.
- `memory_delete` só quando o usuário pedir, por exemplo para algo salvo por engano ou sensível.

## Nunca gravar

Segredos, tokens, senhas, dados de clientes ou pessoais, código, conteúdo de specs e o que se
redescobre lendo o código em segundos.

## Por papel

- **tech-lead** (`/spec`, `/plan`): grava decisões de projeto e, ao fim do plano, as pendências.
  Decisão local de uma única feature fica só no design da feature.
- **developer** (`/build`): consulta antes de implementar. Grava só lições que vão morder de novo,
  não progresso de tarefas.
- **auditor** (`/review`): faz `recall` de decisões e lições com os termos dos arquivos alterados e
  verifica se o diff viola alguma. Grava padrões de problema, não casos pontuais.
- **researcher**: consulta achados antes de pesquisar e reaproveita os recentes, citando a data.
  Grava cada achado com fonte e data; achados que valem para qualquer projeto vão com
  `global_scope=true`.
