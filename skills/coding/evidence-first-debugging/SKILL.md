---
name: evidence-first-debugging
description: "Use when diagnosing lag or bugs: measure, never guess."
version: 1.0.0
author: Davi Kolansinsky (imperat-on), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, profiling, performance, measurement, evidence, root-cause, cdp, electron,
           chromium, long-tasks, tracing, cpu-profile, travamento, lentidao]
    related_skills: [systematic-debugging, investigate-first, verification-before-completion,
                     node-inspect-debugger, python-debugpy]
---

# Evidence-First Debugging

Regra unica, sem excecao: **nenhuma afirmacao de causa sem medicao feita no sistema que
apresentou o sintoma.** "Eu acho que e X" e hipotese, nao diagnostico. Hipoteses viram
diagnostico quando o instrumento — rodando no ambiente real — mostra o numero.

Esta skill existe porque diagnosticos por intuicao ja custaram horas: tres "causas"
anunciadas em sequencia (decode de imagem, logo gigante, loop de IPC), todas plausiveis,
enquanto o bloqueio real de 460 ms continuava. Quando finalmente se mediu com trace e CPU
profile DENTRO do app do usuario, a causa era outra — e ficou obvia em minutos.

## Quando usar

- Qualquer relato de lentidao, engasgo, travamento, "congela e volta", consumo alto.
- Bug que "so acontece as vezes" ou "so com alguns itens" (dado especifico e pista, nao ruido).
- Antes de dizer "encontrei a causa" — o proprio ato de anunciar exige ter medido.
- Depois de corrigir: para provar antes/depois com o MESMO instrumento.

## O sintoma define a categoria (antes de medir)

Use a descricao do usuario para estreitar, nunca para concluir:

| Sintoma relatado | Categoria provavel | Comece medindo |
|---|---|---|
| "engasga", "travadinha" (curto) | frame longo: decode, raster, layout | frames >34 ms + LoAF + trace de decode/raster |
| "congela por segundos e volta" | bloqueio de main thread: loop, I/O sincrono, O(n2), retry | CPU profile (self time por funcao) + LoAF (`scripts`) |
| "so em alguns X" | dado especifico de X (arquivo, tamanho, URL) | inventariar o dado real de X vs um X saudavel |
| "demora a aparecer" | rede, espera assincrona, fallback | resource timing + quando o no monta |
| "piora com o tempo" | acumulo: cache, listeners, memoria | heap/counts em pontos sucessivos |

Um erro de categoria faz voce medir a coisa errada e "descartar" a causa certa. Sempre que
o sintoma mencionar **quanto tempo** (ms vs segundos) ou **qual item** ("tal jogo"), trate
isso como hipotese de alta prioridade.

## Protocolo (cinco passos, nesta ordem)

1. **Reproduza no ambiente real.** Nao em um substituto. Medir num browser separado, num
   clone, numa instancia headless ou num arquivo de teste e util para entender o mecanismo —
   e e INVALIDO como prova do sintoma do usuario, porque o ambiente muda o resultado
   (GPU/campos de composicao, cache, dados reais, extensoes, tamanho de janela).
2. **Capture com instrumento.** Observadores de long task/frames, CPU profile, trace de
   timeline, resource timing — escolhidos pela categoria do passo anterior.
3. **Isole a variavel com A/B no mesmo ambiente.** Ex.: mesmo app, mesmo fluxo, trocando
   SOMENTE o suspeito (A: arquivo atual; B: arquivo trocado). Se o numero muda com a troca,
   voce tem causalidade, nao correlacao.
4. **Corrija a causa, nao o sintoma.** Sintoma (bloquear a UI para nao travar) != causa
   (a arte que entrou gigante pela porta sem limite). Prefira o ponto de entrada (validacao,
   limite, contrato) ao ponto de exibicao.
5. **Re-meca com o MESMO instrumento e mostre antes/depois.** "Melhorou" sem numero e opiniao.
   O relatorio final tem: numero antes, numero depois, e o comando/roteiro que produziu os dois.

## Ferramentas por ambiente

**Electron / Chromium (UI e app desktop)** — a mais usada:

- Abrir com porta de inspecao: `electron . --remote-debugging-port=9222`. Em app empacotado,
  `app.commandLine.appendSwitch('remote-debugging-port', '9222')` no main.
- Falar CDP sem dependencia: `WebSocket` global do Node 22+, com `Runtime.enable`,
  `Runtime.evaluate` (`awaitPromise: true`), `Input.dispatchKeyEvent`, `Page.bringToFront`
  (sem foco, teclas sinteticas sao ignoradas — verifique lendo o estado a cada passo).
- Long tasks e frames: `PerformanceObserver({entryTypes:['longtask']})`, `LoAF`
  (`long-animation-frame`, tem `blockingDuration` e `scripts`), e um loop de `requestAnimationFrame`
  registrando deltas >34 ms.
- CPU: `Profiler.enable` + `Profiler.start`/`Profiler.stop` — leia o **self time por funcao**.
  `(program)` dominando com JS ~0 significa codigo NATIVO (decode/raster), nao React.
- Trace detalhado: `Tracing.start` com `devtools.timeline` — procura `RunTask`, `ImageDecodeTask`,
  `Decode Image{format}`, `RasterTask`, `Layout`, `UpdateLayer`.
- Decode de imagem isolado: `new Image(); im.src = url; await im.decode()` e meca o tempo e
  `naturalWidth x naturalHeight`. Compare pixels, nao KB.

**Node/CLI:** `--inspect` + `node --cpu-prof`; `process.hrtime.bigint()` em volta do suspeito.

**Rede:** tempo por recurso (`resource timing`/`curl -w`), com e sem cache.

**Backend/generico:** logs correlacionaveis, spans, e o mesmo principio: medir no ambiente
que apresenta o problema, com numero, antes e depois.

## Armadilhas que ja custaram caro

- **Medir num substituto e generalizar.** O mecanismo pode confirmar num ambiente e o sintoma
  real viver em outro (cache, GPU, dados do usuario). Mecanismo != sintoma.
- **Anunciar causa antes do numero.** "Encontrei!" seguido de correcao sem medicao quebra a
  confianca — e frequentemente esta errado, porque o sintoma tem multiplas camadas.
- **Correlacao como causa.** O recurso carregou na hora do engasgo — e o engasgo pode ser o
  decode dele OU outra coisa no mesmo frame. So o A/B no mesmo ambiente separa.
- **Olhar KB em vez de pixels.** Uma imagem de 226 KB pode ter 44 megapixels; o custo e o
  bitmap decodificado, nao o download. E PNG de 44 Mpx ainda "decodifica" — so que em 300 ms.
- **Descartar pelo ambiente errado.** "No meu teste deu 0 ms" enquanto o problema tem outra
  variavel (arquivo local do usuario, override, cache). Inventarie o dado REAL do usuario.
- **Confiar em relato de agente/worker.** Resultado reportado e comunicacao, nao evidencia:
  re-execute ou leia o artefato (trace, JSON, arquivo) com os proprios olhos.
- **Consertar o sintoma e cantar vitoria.** Esconder o icone quebrado nao impede o download
  do arquivo gigante; limite na entrada vale mais que `onError` na saida.

## Checklist antes de dizer "resolvido"

1. Reproduzi o sintoma no ambiente real? (nao so entendi mecanicamente)
2. Tenho o numero ANTES, medido com instrumento? (frame, ms, contagem, perfil)
3. Isolei a variavel com A/B no mesmo ambiente?
4. Corrigi a causa (entrada/contrato), nao o sintoma?
5. Re-medi com o MESMO instrumento e tenho o numero DEPOIS?
6. O artefato existe (trace, JSON, relatorio) e eu olhei com os proprios olhos?
7. A correcao fecha a classe inteira do bug, nao so a instancia que apareceu?

Assumir o custo: medir custa ~10 minutos e convence; chutar custa horas de frustracao,
perda de confianca e correcoes que nao corrigem.
