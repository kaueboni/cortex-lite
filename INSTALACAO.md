# Instalação do cortex-lite

Guia passo a passo para instalar o plugin de memória no Claude Code e usá-lo nos seus projetos.
O plugin é instalado **uma vez por máquina** e vale para todos os projetos; cada projeto tem a
sua própria memória, separada pelo nome do repositório git.

---

## 1. Pré-requisitos

| Item | Como verificar | Observação |
| --- | --- | --- |
| Claude Code | `claude --version` | Qualquer versão recente com suporte a plugins. |
| Python 3.10+ | `py --version` (Windows) ou `python3 --version` | É a única dependência. Nada de `pip install`. |
| Acesso ao repositório | `git ls-remote https://github.com/kaueboni/cortex-lite` | Só para instalar direto do GitHub. O repositório é privado. |

---

## 2. Instalar o plugin (uma vez por máquina)

Escolha **uma** das opções, conforme a rede permitir.

### Opção A — Direto do GitHub

Dentro do Claude Code:

```
/plugin marketplace add kaueboni/cortex-lite
/plugin install cortex-lite@cortex-lite
```

### Opção B — De uma pasta local (rede corporativa que bloqueia o GitHub)

1. Copie ou clone o repositório para uma pasta fixa:
   ```powershell
   git clone https://github.com/kaueboni/cortex-lite C:\ferramentas\cortex-lite
   ```
   Sem acesso ao git, baixe o ZIP do repositório e extraia na mesma pasta.
2. Dentro do Claude Code:
   ```
   /plugin marketplace add C:/ferramentas/cortex-lite
   /plugin install cortex-lite@cortex-lite
   ```

Nessa opção o plugin roda direto da pasta. Para atualizar: `git pull` na pasta e `/reload-plugins`
no Claude Code.

---

## 3. Informar o comando do Python

Durante a instalação, o Claude Code pergunta o **Comando do Python**:

| Sistema | Valor |
| --- | --- |
| Windows | `py` (padrão) |
| Windows, se `py` não existir | caminho completo, ex.: `C:/Users/<você>/AppData/Local/Programs/Python/Python312/python.exe` |
| macOS / Linux | `python3` |

Para alterar depois: `/plugin configure cortex-lite@cortex-lite`.

Se a pergunta não aparecer (instalação pela linha de comando), passe o valor direto:

```
claude plugin install cortex-lite@cortex-lite --config python=py
```

---

## 4. Verificar a instalação

1. **Ambiente da máquina:**
   ```powershell
   py C:/ferramentas/cortex-lite/run.py doctor
   ```
   Todas as linhas devem sair `[ok]`. Na opção A, rode o mesmo comando a partir de um clone
   qualquer do repositório.
2. **Plugin carregado:** em `/plugin`, o `cortex-lite` deve aparecer como habilitado e sem erros.
3. **Teste de ponta a ponta**, dentro de um repositório git:
   - Numa sessão, peça: *"Salve na memória, como decisão: usamos Postgres por causa do JSONB."*
   - Abra uma **nova** sessão no mesmo projeto e pergunte: *"Qual banco usamos e por quê?"*
   - A resposta deve vir da memória, sem o agente precisar procurar no código.
   - Depois, peça para apagar a memória de teste.

---

## 5. Liberar as ferramentas sem confirmação (recomendado)

Sem isto, o Claude Code pede permissão a cada consulta ou gravação. Acrescente em
`%USERPROFILE%\.claude\settings.json` (ou `~/.claude/settings.json`):

```json
{
  "permissions": {
    "allow": [
      "mcp__plugin_cortex-lite_memoria__recall",
      "mcp__plugin_cortex-lite_memoria__memory_get",
      "mcp__plugin_cortex-lite_memoria__memory_list",
      "mcp__plugin_cortex-lite_memoria__memory_save"
    ]
  }
}
```

`memory_supersede` e `memory_delete` ficam de fora de propósito: alteram o histórico e merecem
confirmação.

---

## 6. Habilitar num projeto para o time (opcional)

Para que quem abrir o projeto receba a oferta de instalar o plugin, versione no repositório o
arquivo `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "cortex-lite": {
      "source": { "source": "github", "repo": "kaueboni/cortex-lite" }
    }
  },
  "enabledPlugins": {
    "cortex-lite@cortex-lite": true
  }
}
```

Cada pessoa ainda informa o próprio comando do Python e tem o próprio banco local: a memória
**não** é compartilhada entre máquinas. Para o time enxergar as decisões, use o export do passo 7.

Para **desligar** o plugin num projeto específico, use `"cortex-lite@cortex-lite": false` no
`.claude/settings.local.json` desse projeto.

---

## 7. Integrar ao framework SDD

O plugin já traz a skill `memoria`, que orienta os agentes (tech-lead, developer, auditor,
researcher) sobre quando consultar e o que gravar. Dois ajustes opcionais:

- **Comportamento obrigatório por agente:** cole os trechos de [`AGENTES.md`](AGENTES.md) no prompt
  de cada agente.
- **Revisão em PR:** a cada release, exporte a memória do projeto e versione o markdown:
  ```powershell
  py C:/ferramentas/cortex-lite/run.py export > docs/MEMORIA.md
  ```
  Rode o comando na pasta do projeto: o projeto é detectado pelo repositório git atual.

O banco fica fora do repositório (`~/.cortexlite/memoria.db`), então não há nada a acrescentar
ao `.gitignore`.

---

## 8. Problemas comuns

| Sintoma | Causa provável | Solução |
| --- | --- | --- |
| Ferramentas `memoria` não aparecem | Comando do Python errado | `/plugin configure cortex-lite@cortex-lite` e use o caminho completo do `python.exe`. |
| `py` abre a Microsoft Store ou não é encontrado | Python não instalado pelo instalador oficial | Instale pelo python.org ou informe o caminho completo do executável. |
| `doctor` falha em `sqlite` (FTS5) | Python compilado sem FTS5 (raro no Windows) | Use o Python oficial do python.org. |
| Nada é injetado no início da sessão | Projeto ainda sem memórias, ou fora de um repositório git | Normal. Fora do git, o projeto é o nome da pasta. |
| Memória de um projeto aparece em outro | Dois repositórios com o mesmo nome de pasta | Defina `CORTEXLITE_PROJECT` com um nome único naquele projeto. |
| Quer pausar sem desinstalar | — | Variável de ambiente `CORTEXLITE_DISABLE=1` desliga os hooks. |
| Ver erros dos hooks | — | Variável de ambiente `CORTEXLITE_DEBUG=1`. |

---

## 9. Desinstalar

```
/plugin uninstall cortex-lite@cortex-lite
/plugin marketplace remove cortex-lite
```

As memórias continuam em `~/.cortexlite/memoria.db`. Apague esse arquivo se quiser removê-las
também.
