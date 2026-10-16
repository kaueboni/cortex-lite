# Integração com o framework SDD

Os trechos abaixo vão no prompt de cada agente (`.claude/agents/<agente>.md`) e nos comandos
(`/spec`, `/plan`, `/build`, `/review`). A regra geral: **quem decide grava, quem executa consulta.**

## Regra comum (todos os agentes)

```markdown
## Memória (cortex-lite)
- O início da sessão já traz um índice das memórias do projeto. Leia com `memory_get` só as que
  importam para a tarefa atual.
- Antes de propor algo, faça `recall` com 2 a 6 palavras-chave do assunto (nomes, siglas, termos
  técnicos). Se uma memória vigente contradiz sua proposta, siga a memória ou diga explicitamente
  que propõe substituí-la.
- Nunca grave segredos, credenciais, dados de clientes, código ou o conteúdo de specs.
```

## tech-lead (`/spec`, `/plan`)

```markdown
- Ao fechar uma decisão que outras features precisam respeitar, grave com
  `memory_save(kind="decisao", agent="tech-lead", title="<assunto>: <escolha>")`.
  No content, diga o que foi decidido, o porquê e do que se abriu mão.
- Se a decisão substitui outra, passe `supersedes=["<id antigo>"]`. Não apague a antiga.
- Ao terminar o /plan, grave o que ficou em aberto com `kind="pendencia"`.
- Decisão local de uma única feature fica só no design.md, não na memória.
```

## developer (`/build`)

```markdown
- Antes de implementar uma task, faça `recall` com o nome do módulo e da tecnologia envolvida.
- Só grave quando descobrir algo que vai morder de novo, com `kind="licao"` e `agent="developer"`.
  Exemplo: "o mock do cliente HTTP precisa de X senão o teste passa falso".
- Não grave progresso de tarefas: isso fica no tasks.md e no handoff.
```

## auditor (`/review`)

```markdown
- Antes de revisar, faça `recall` com `kind="licao"` e com `kind="decisao"` usando os termos dos
  arquivos alterados. Verifique se o diff viola alguma decisão vigente ou repete uma lição.
- Ao encontrar um problema que pode voltar, grave com `kind="licao"` e `agent="auditor"`,
  descrevendo o padrão do problema e não o caso pontual.
- Se uma lição antiga já não se aplica, use `memory_supersede`.
```

## researcher

```markdown
- Antes de pesquisar, faça `recall` do tema com `kind="achado"`. Se houver um achado recente e
  suficiente, use-o em vez de pesquisar de novo e diga a data dele.
- Ao concluir, grave cada achado reutilizável com `kind="achado"` e `agent="researcher"`, incluindo
  a fonte e a data. Exemplos: limites de API, versões, preços, comportamento de biblioteca.
- Achado sobre algo que muda rápido: inclua "verificar após <data>" no content.
- Use `global_scope=true` quando o achado não for específico deste projeto.
```

## Revisão humana

De tempos em tempos, ou a cada release, rode `py run.py export > docs/MEMORIA.md` e abra um PR.
Assim a memória continua revisável como o resto do harness. Se algo estiver errado, corrija com
`memory_save` usando o mesmo `id`, ou marque como substituído.
