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

**Do GitHub** (se o repositório estiver privado, o git da máquina precisa ter acesso a ele):

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
py C:/ferramentas/cortex-lite/run.py doctor          # Windows
python3 ~/ferramentas/cortex-lite/run.py doctor      # macOS / Linux
```

### Liberar as ferramentas sem confirmação (opcional)

Em `%USERPROFILE%\.claude\settings.json` (Windows) ou `~/.claude/settings.json` (macOS / Linux):

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
| Skill `memoria` | Ensina os agentes quando consultar, o que gravar e com qual `kind`, por perfil de uso (leitor, pesquisador, decisor, executor, revisor). |

Não há captura automática: só entra no banco o que um agente salvar explicitamente. Para integrar a
agentes e subagentes, veja [`AGENTES.md`](AGENTES.md).

## Tipos de memória (`kind`)

`decisao` · `licao` · `achado` · `fato` · `preferencia` · `pendencia`

## Interface estável

O cortex-lite não conhece nenhum fluxo ou squad: quem integra decide qual agente usa qual perfil.
Para isso funcionar, três coisas são **interface pública** e só mudam com versão maior e nota de
migração no [`CHANGELOG.md`](CHANGELOG.md):

- **Ferramentas e efeito:** leitura (`recall`, `memory_get`, `memory_list`), escrita (`memory_save`,
  `memory_supersede`) e destrutiva, só humano (`memory_delete`). Nome completo num subagente:
  `mcp__plugin_cortex-lite_memoria__<ferramenta>`.
- **Tipos de memória:** os seis `kind` acima.
- **Perfis de uso:** leitor, pesquisador, decisor, executor e revisor.

| Perfil | Ferramentas | O que grava |
| --- | --- | --- |
| leitor | `recall`, `memory_get`, `memory_list` | nada |
| pesquisador | + `memory_save` | `achado`, com fonte e data |
| decisor | + `memory_save`, `memory_supersede` | `decisao` e `pendencia` |
| executor | + `memory_save` | `licao` que vai se repetir |
| revisor | + `memory_save`, `memory_supersede` | `licao` de padrões recorrentes |

### Subagentes

Os hooks agem só na **sessão principal**: o índice do início da sessão e o recall automático não
chegam a subagentes. Um subagente precisa (1) ter as ferramentas listadas com o nome completo no
campo `tools:` e (2) fazer `recall` por conta própria; pré-carregar a skill `cortex-lite:memoria` no
cabeçalho ajuda. Exemplos prontos em [`AGENTES.md`](AGENTES.md).

## O que vai onde

| Onde | O quê |
| --- | --- |
| cortex-lite | O porquê: decisões, lições, achados, pendências e fatos estáveis. Buscado sob demanda. |
| `CLAUDE.md` e afins (carregados em toda sessão) | Só regras curtas. Decisões e lições saem daqui e vão para a memória. |
| Registro de progresso do projeto | Estado atual e histórico de entregas, não decisões. |
| Specs, planos, tarefas e código | Continuam nos arquivos do repositório. |
| Memória automática do Claude Code | Veja abaixo. |

**Migrar da memória automática do Claude Code** (`~/.claude/projects/<projeto>/memory/`):
1. leia o `MEMORY.md` e os arquivos da pasta;
2. classifique cada item: conhecimento do projeto, preferência pessoal ou desatualizado;
3. grave o conhecimento do projeto com `memory_save` (`decisao`, `licao` ou `fato`) e, se quiser,
   as preferências como `preferencia` com `global_scope=true`;
4. desligue a memória automática em `/memory`, para não carregar as duas.

## Tokens: quando economiza

- **Custo fixo:** o índice do início da sessão (até `CORTEXLITE_SESSION_MAX` linhas) e o recall por
  prompt (até `CORTEXLITE_RECALL_BUDGET` caracteres, e só quando há correspondência relevante).
- **Onde economiza:** troca conteúdo carregado em **toda** sessão (o `CLAUDE.md` e até 200 linhas
  ou 25 KB do `MEMORY.md` da memória automática) por busca sob demanda; evita que agentes
  redescubram decisões lendo o código; reduz retrabalho.
- **Condição:** só economiza se esse conteúdo **sair** do que é carregado sempre. Duplicar a mesma
  decisão no `CLAUDE.md` e na memória custa mais, não menos.
- **Como medir:** compare tokens por feature antes e depois (o plugin
  [agentmeter](https://github.com/kaueboni/agentmeter) separa por subagente).

## Time

O banco é **local de cada máquina**. A memória chega ao time pelo export:

```
py run.py export > docs/MEMORIA.md
```

Gere ao fim de cada feature (ou release), versione e revise no PR. Um dev novo lê o
`docs/MEMORIA.md` para se situar. Não há importação do export para o banco de outra máquina:
quando dois devs gravam, cada um tem o próprio banco e o `docs/MEMORIA.md` é o ponto de encontro.

## CLI

No macOS e Linux, troque `py` por `python3`.

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
