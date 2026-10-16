# cortex-lite

Plugin do Claude Code que dá memória persistente aos seus agentes, entre sessões e entre agentes.
Inspirado no [CortexDB](https://github.com/liliang-cn/cortexdb) (MIT), reduzido ao que um framework
SDD precisa: lembrar decisões, lições e achados, sem binário, sem servidor, sem `pip install` e sem
nada saindo da máquina.

- **Só Python 3.10+.** Tudo usa a biblioteca padrão, inclusive o servidor MCP.
- **Um arquivo SQLite** (`~/.cortexlite/memoria.db`) com busca full-text (FTS5/BM25) que ignora
  acentos e entende plural ("listagem" acha "listagens").
- **Por projeto:** o projeto é o nome do repositório git. Memórias globais (como preferências) valem
  em todos os projetos.
- **Histórico sem ruído:** uma decisão substituída fica guardada, mas sai do recall.
- **Revisável:** `export` gera um markdown para versionar e revisar em PR.

## Instalação

Uma vez por máquina; vale para todos os projetos.

**Do GitHub** (o repositório é privado, então o git da máquina precisa ter acesso a ele):

```
/plugin marketplace add kaueboni/cortex-lite
/plugin install cortex-lite@cortex-lite
```

**De uma pasta local**, por exemplo quando a rede bloqueia o GitHub: copie ou clone o repositório
para `C:\ferramentas\cortex-lite` e rode

```
/plugin marketplace add C:/ferramentas/cortex-lite
/plugin install cortex-lite@cortex-lite
```

Instalado de uma pasta local, o plugin roda direto dela: para atualizar, basta um `git pull` ali e
`/reload-plugins`.

Na instalação, o Claude Code pergunta o **comando do Python**:

| Sistema | Valor |
| --- | --- |
| Windows | `py` (padrão) ou o caminho completo, como `C:/Users/<você>/AppData/Local/Programs/Python/Python312/python.exe` |
| macOS / Linux | `python3` |

Para mudar depois: `/plugin configure cortex-lite@cortex-lite`.

Passo a passo completo, verificação e problemas comuns: [`INSTALACAO.md`](INSTALACAO.md).

Para conferir o Python e o SQLite da máquina:

```
py C:/ferramentas/cortex-lite/run.py doctor
```

### Liberar as ferramentas sem confirmação (opcional)

Em `%USERPROFILE%\.claude\settings.json`:

```json
"permissions": {
  "allow": [
    "mcp__plugin_cortex-lite_memoria__recall",
    "mcp__plugin_cortex-lite_memoria__memory_get",
    "mcp__plugin_cortex-lite_memoria__memory_list",
    "mcp__plugin_cortex-lite_memoria__memory_save"
  ]
}
```

## O que o plugin instala

| Peça | O que faz |
| --- | --- |
| Hook `SessionStart` | Injeta um índice com uma linha por memória vigente do projeto (até 20). |
| Hook `UserPromptSubmit` | Busca memórias que casam com o prompt e injeta até ~1200 caracteres. Prompts como "ok" e "segue" não disparam nada, e memórias que casam com uma única palavra solta são descartadas. |
| Servidor MCP `memoria` | Ferramentas `recall`, `memory_save`, `memory_get`, `memory_list`, `memory_supersede` e `memory_delete`. |
| Skill `memoria` | Ensina os agentes quando consultar, o que gravar e com qual `kind`, por papel (tech-lead, developer, auditor, researcher). |

Não há captura automática: só entra no banco o que um agente salvar explicitamente. Para regras
mais rígidas por agente, veja [`AGENTES.md`](AGENTES.md).

## Tipos de memória (`kind`)

`decisao` · `licao` · `achado` · `fato` · `preferencia` · `pendencia`

## CLI

```
py run.py search "rate limit consumidor"     # o que o recall veria
py run.py list                                # memórias vigentes do projeto atual
py run.py save "texto" --kind decisao --title "..."
py run.py export > docs/MEMORIA.md            # markdown para revisar em PR
py run.py stats                               # contagem por projeto
```

## Variáveis de ambiente

| Variável | Padrão | Uso |
| --- | --- | --- |
| `CORTEXLITE_PATH` | `~/.cortexlite/memoria.db` | Arquivo do banco. |
| `CORTEXLITE_PROJECT` | nome do repo git | Força o nome do projeto (útil se dois repos têm o mesmo nome). |
| `CORTEXLITE_RECALL_BUDGET` | `1200` | Máximo de caracteres injetados por prompt. |
| `CORTEXLITE_RECALL_TOP_K` | `4` | Máximo de memórias injetadas por prompt. |
| `CORTEXLITE_SESSION_MAX` | `20` | Itens no índice do início da sessão. |
| `CORTEXLITE_DISABLE` | — | `1` desliga os hooks sem desinstalar. |
| `CORTEXLITE_DEBUG` | — | `1` mostra erros dos hooks no stderr. |

## O que não guardar

Segredos, credenciais, dados de clientes, código e o conteúdo das specs. As specs continuam em
markdown no repositório. A memória guarda o *porquê*: decisões, lições e achados.

## Testes

```
py -m pip install --user pytest
py -m pytest tests
```
