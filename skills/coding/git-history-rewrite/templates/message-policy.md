# Politica de redacao do historico - <projeto>

Copie para o diretorio de trabalho da reescrita e preencha. Este arquivo e o
contrato entregue a quem reescreve as mensagens e a checklist de validacao.

## Idioma e formato

- Idioma das mensagens: <ex.: portugues do Brasil>. Mensagens antigas em outro
  idioma entram no lote de traducao.
- Formato: `tipo(escopo): descricao`, sem ponto final, sem emoji, sem caixa alta
  de enfase, sem primeira pessoa, sem reticencias.
- Tipos permitidos: feat, fix, chore, refactor, docs, test, perf, style, ci,
  build, revert. Escopo em minusculas, sem acento, uma palavra.
- Sujeito: no maximo ~90 caracteres. O que passar disso vira o primeiro paragrafo
  do corpo, sem perder informacao.
- Corpo: paragrafos curtos ou bullets `- `, quebra de linha em ~76 colunas.
- Equivalencias: `release:` -> `chore(release):`; `cleanup(x):` -> `refactor(x):`;
  prefixos entre colchetes saem.

## Termos proibidos e como substituir

Circunvencao de DRM / pirataria (nunca aparecem, nem no sujeito nem no corpo):

| termo | substituir por |
|---|---|
| <termo 1> | <frase tecnica neutra> |
| <termo 2> | <frase tecnica neutra> |

Ferramentas, servicos, grupos e foruns de terceiros que a politica remove:
<lista>

Termos contextuais - proibidos SO na frase que promete o ilicito, permitidos
quando descrevem funcionalidade legitima do produto: <lista>

## O que PERMANECE

- Ferramentas legitimas de terceiros: <ex.: Proton, Wine, aria2, yt-dlp>.
- Nomes de arquivo, funcao, IPC, teclas e marcas do produto.
- Numeros, medicoes e o porque tecnico de cada mudanca: a reescrita nao corta
  explicacao.

## Rodape e ruido

- Remover rodape de agente/IA (`Generated with`, `Co-authored-by: <agente>`,
  emoji de robo) e nome de modelo.
- Nao inventar fato que nao esteja na mensagem original.
- Nao citar caminho absoluto da maquina do autor nem dado pessoal.

## Validacao obrigatoria da saida

1. JSON carrega e o conjunto de chaves e identico ao dos hashes de entrada.
2. Todo sujeito casa `^(feat|fix|chore|refactor|docs|test|perf|style|ci|build|revert)(\([a-z0-9-]+\))?!?: .+`.
3. Nenhum termo proibido em sujeito ou corpo.
4. Corpo que existia continua existindo, com o mesmo tamanho ou maior.
5. Contagem de bullets preservada (perda de estrutura aparece como menos `\n- `).
6. Nenhum sujeito acima do limite de caracteres; nenhuma mensagem vazia.
