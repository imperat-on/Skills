# INSTALL-FOR-AGENT — cole isto na IA da sua CLI

> Bloco abaixo é para ser copiado inteiro e colado num agente com acesso a
> terminal (Claude Code, Codex, Hermes Agent, OpenCode, Prime Agent, Gemini CLI,
> Cursor…). Ele instala as skills, e opcionalmente os hooks, e verifica o
> resultado. Não precisa de contexto anterior.

---

Você vai instalar um kit de skills Agent Skills (`SKILL.md`) a partir do
repositório https://github.com/imperat-on/Skills nesta máquina. Execute os passos
na ordem, mostre o resultado de cada verificação e **não pule o passo 4**.

1. Clone e inspecione antes de instalar:

   ```bash
   git clone https://github.com/imperat-on/Skills ~/Skills 2>/dev/null || (cd ~/Skills && git pull)
   cd ~/Skills
   ls skills/ && head -40 README.md
   ```

2. Valide que todo `SKILL.md` está conforme a spec Agent Skills e que os hooks
   passam nos testes (nada é instalado ainda):

   ```bash
   python3 tools/validate-skills.py     # esperado: 0 erros
   bash tools/test-hooks.sh             # esperado: PASS: 52   FAIL: 0
   ```

3. Descubra onde ESTA CLI lê skills e instale no lugar certo. Primeiro veja o
   plano; depois execute:

   ```bash
   ./install.sh --list                  # o que iria para quais diretórios
   ./install.sh                         # tier core (32 skills) nas CLIs detectadas
   # ./install.sh --tier all            # se o usuário quiser as 123
   ```

   O instalador usa symlink por padrão (assim `git pull` atualiza tudo) e não
   sobrescreve skill que já exista no destino — se pular algo, me diga o quê e
   pergunte ao usuário se pode usar `--force`.

4. Hooks: **não instale sem revisar**. Mostre ao usuário o que cada script
   bloqueia e só depois:

   ```bash
   ls hooks/scripts/ && ./hooks/install-hooks.sh --dry-run
   # após o ok do usuário:
   ./hooks/install-hooks.sh
   ```

   Eles bloqueiam comandos destrutivos e acesso a credenciais. Se o usuário não
   quiser, pare aqui — as skills funcionam sem os hooks.

5. **MCPs: não estão neste kit** (de propósito — servidor MCP entra em toda
   chamada da API e infla o contexto). Se o usuário pedir, o catálogo com versões
   conferidas, o gerador de config por CLI e o instalador estão em
   `~/Documents/projects/docs-davi/mcp-catalogo/`. Explique que `filesystem` e
   `github` ampliam muito o acesso e não devem ser ligados sem necessidade.

6. Confirme que a CLI enxerga as skills — reinicie a sessão (o índice é lido no
   start) e rode:

   - Claude Code / Codex: `/skills`
   - Hermes: `skills_list`
   - OpenCode / Prime Agent: a lista aparece no prompt de sistema; em Prime Agent
     dá para forçar com `/skill:<nome>`

   Liste os nomes encontrados e compare com as primeiras linhas de `CATALOG.md`.

Regras: não invente caminhos que não estejam em `README.md` §"Onde cada CLI lê as
skills"; não edite arquivos dentro de `skills/` (são cópias dos originais, com
hash em `manifest.json`); não commite chave nenhuma neste repositório.

<!-- v1 — 2026-09-16 -->
