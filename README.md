# cortex-lite

Memória persistente para os agentes do Claude Code, entre sessões e entre agentes.
Inspirado no [CortexDB](https://github.com/liliang-cn/cortexdb) (MIT), reduzido ao que um framework
SDD precisa: lembrar decisões, lições e achados, sem binário, sem servidor e sem nada saindo da máquina.

- **Um arquivo SQLite** (`%USERPROFILE%\.cortexlite\memoria.db`), com busca full-text FTS5/BM25
  que ignora acentos.
- **Python puro.** Os hooks e a CLI usam só a biblioteca padrão. O servidor MCP precisa do pacote `mcp`.
- **Por projeto:** o projeto é o nome do repositório git. Memórias globais (como preferências)
  valem em todos os projetos.
- **Histórico sem ruído:** uma decisão substituída fica guardada, mas sai do recall.
- **Revisável:** `export` gera um markdown para versionar e revisar em PR.

## Instalação no Windows

Pré-requisito: Python 3.10+ (`py --version`).

1. Copie a pasta `cortex-lite` para `C:\ferramentas\cortex-lite`. Se usar outro caminho, troque-o nos
   comandos abaixo e use barras normais (`/`).
2. Instale o SDK MCP:
   ```powershell
   py -m pip install --user "mcp>=1.2"
   ```
   Se a empresa tiver um espelho do PyPI, acrescente `--index-url <url-do-espelho>`.
3. Verifique a instalação:
   ```powershell
   py C:/ferramentas/cortex-lite/run.py doctor
   ```
   Todas as linhas devem sair `[ok]`.
4. Registre o servidor MCP para todos os projetos:
   ```powershell
   claude mcp add cortex-lite --scope user -- py C:/ferramentas/cortex-lite/run.py serve
   ```
5. Hooks e permissões: copie os blocos `hooks` e `permissions` de
   [`settings.example.json`](settings.example.json) para `%USERPROFILE%\.claude\settings.json`,
   juntando com o que já existir lá.
6. Reinicie o Claude Code e teste:
   ```powershell
   py C:/ferramentas/cortex-lite/run.py save "Teste de memória do cortex-lite" --kind fato
   ```
   Numa nova sessão, o início deve listar essa memória. Depois disso, apague o teste com
   `memory_delete`.

Se `py` não for encontrado pelos hooks (eles rodam pelo Git Bash), troque `py` pelo caminho
completo, por exemplo `C:/Users/<você>/AppData/Local/Programs/Python/Python312/python.exe`.

## O que acontece em cada sessão

| Momento | O que o cortex-lite faz |
| --- | --- |
| Início da sessão | Injeta um índice com uma linha por memória vigente do projeto (até 20). |
| Cada prompt | Busca memórias que casam com o prompt e injeta até ~1200 caracteres. Prompts como "ok" e "segue" não disparam nada, e memórias que casam com só uma palavra solta são descartadas. |
| Quando o agente decide | Usa as ferramentas `recall`, `memory_save`, `memory_get`, `memory_list`, `memory_supersede` e `memory_delete`. |

Não há captura automática: só entra no banco o que um agente salvar explicitamente. Assim nenhuma
memória errada é gravada sem alguém ter decidido isso.

## Tipos de memória (`kind`)

`decisao` · `licao` · `achado` · `fato` · `preferencia` · `pendencia`

## CLI

```powershell
py run.py search "rate limit consumidor"     # o que o recall veria
py run.py list                                # memórias vigentes do projeto atual
py run.py export > docs/MEMORIA.md            # markdown para revisar em PR
py run.py stats                               # contagem por projeto
```

## Variáveis de ambiente

| Variável | Padrão | Uso |
| --- | --- | --- |
| `CORTEXLITE_PATH` | `~/.cortexlite/memoria.db` | Arquivo do banco. |
| `CORTEXLITE_PROJECT` | nome do repo git | Força o nome do projeto. |
| `CORTEXLITE_RECALL_BUDGET` | `1200` | Máximo de caracteres injetados por prompt. |
| `CORTEXLITE_RECALL_TOP_K` | `4` | Máximo de memórias injetadas por prompt. |
| `CORTEXLITE_SESSION_MAX` | `20` | Itens no índice do início da sessão. |
| `CORTEXLITE_DISABLE` | — | `1` desliga os hooks sem desinstalar. |
| `CORTEXLITE_DEBUG` | — | `1` mostra erros dos hooks no stderr. |

## O que não guardar

Segredos, credenciais, dados de clientes, código e o conteúdo das specs. As specs continuam em
markdown no repositório. A memória guarda o *porquê*: decisões, lições e achados.

## Testes

```powershell
py -m pip install --user pytest
py -m pytest tests
```
