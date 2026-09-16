#!/usr/bin/env python3
"""Remove CSS rules/selectors that only use dead classes.

Usage:
  python3 css_surgery.py STYLESHEET DEAD_JSON [--apply]

DEAD_JSON comes from scripts/dead_scan.py. Dry-run by default: it prints what
would go, plus the safety assertions. Requires flat CSS (max brace depth 2, no
@apply/@layer/@utility).
"""
import argparse
import glob
import json
import os
import re


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("css")
    ap.add_argument("dead_json")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    mortas = set(json.load(open(a.dead_json))["dead_classes"])
    texto = open(a.css, encoding="utf-8").read()
    linhas = texto.split("\n")
    n = len(linhas)
    originais = set(re.findall(r"\.([a-zA-Z][\w-]*)", texto))

    # ---- top-level blocks (flat CSS: header line + balanced braces) ----
    blocos = []
    i = 0
    while i < n:
        l = linhas[i]
        if not l.strip() or l.strip().startswith(("/*", "*", "*/")):
            i += 1
            continue
        ini = i
        cabeca = []
        while i < n and "{" not in linhas[i]:
            cabeca.append(linhas[i])
            i += 1
        if i >= n:
            break
        cabeca.append(linhas[i])
        sel = " ".join(x.strip() for x in cabeca).split("{")[0].strip()
        depth = 0
        j = i
        while j < n:
            depth += linhas[j].count("{") - linhas[j].count("}")
            if depth == 0:
                break
            j += 1
        blocos.append({"ini": ini, "fim": j, "sel": sel})
        i = j + 1
    print("top-level blocks:", len(blocos))

    def seletor_morto(sel):
        return any(c in mortas for c in re.findall(r"\.([a-zA-Z][\w-]*)", sel))

    apagar = set()
    regras = podados = cond_vazios = 0
    avisos = []

    for b in blocos:
        sel, ini, fim = b["sel"], b["ini"], b["fim"]
        if sel.startswith(("@keyframes", "@font-face", "@theme", "@custom-variant")):
            continue
        if sel.startswith(("@media", "@supports")):
            corpo = "\n".join(linhas[ini:fim + 1])
            subs = [s for s in re.findall(r"([^{}]+)\{", corpo) if not s.strip().startswith("@")]
            if subs and not [s for s in subs if not seletor_morto(s)]:
                apagar |= set(range(ini, fim + 1))
                cond_vazios += 1
            else:
                podados += len([s for s in subs if seletor_morto(s)])
            continue
        partes = [p.strip() for p in sel.split(",") if p.strip()]
        mortas_aqui = [p for p in partes if seletor_morto(p)]
        vivas = [p for p in partes if not seletor_morto(p)]
        if not mortas_aqui:
            continue
        # a custom property defined here but consumed elsewhere would be lost
        bloco = "\n".join(linhas[ini:fim + 1])
        for v in re.findall(r"(--[\w-]+)\s*:", bloco):
            fora = len(re.findall(r"var\(\s*" + re.escape(v) + r"\s*[,)]", texto)) - len(
                re.findall(r"var\(\s*" + re.escape(v) + r"\s*[,)]", bloco)
            )
            if fora > 0:
                avisos.append((v, sel[:60]))
        if not vivas:
            apagar |= set(range(ini, fim + 1))
            regras += 1
        else:
            podados += len(mortas_aqui)

    # ---- orphan keyframes: not in surviving CSS, not anywhere in code ----
    codigo = ""
    base = os.path.dirname(os.path.abspath(a.css))
    for raiz in ("", "electron"):
        for ext in ("*.ts", "*.tsx", "*.js", "*.cjs", "*.mjs"):
            for f in glob.glob(os.path.join(base, raiz, "**", ext), recursive=True):
                codigo += open(f, encoding="utf-8", errors="replace").read()
    kf = []
    for b in blocos:
        if not b["sel"].startswith("@keyframes"):
            continue
        nome = b["sel"].split()[1].strip()
        restante = "\n".join(l for k, l in enumerate(linhas) if k not in apagar)
        em_codigo = re.search(r"(?<![\w-])" + re.escape(nome) + r"(?![\w-])", codigo)
        em_css = re.search(
            r"animation[^;{}]*?(?<![\w-])" + re.escape(nome) + r"(?![\w-])", restante
        )
        if not em_codigo and not em_css:
            kf.append(nome)
            apagar |= set(range(b["ini"], b["fim"] + 1))

    restante = "\n".join(l for k, l in enumerate(linhas) if k not in apagar)
    sobreviventes = set(re.findall(r"\.([a-zA-Z][\w-]*)", restante))
    perdidas = sorted(originais - mortas - sobreviventes)

    print("\n=== dry-run ===")
    print(f"  rules removed whole      : {regras}")
    print(f"  selectors pruned         : {podados}")
    print(f"  @media/@supports emptied : {cond_vazios}")
    print(f"  orphan @keyframes removed: {len(kf)} {kf}")
    print(f"  lines removed            : {len(apagar)} of {n}")
    print("\n=== assertions ===")
    saude = perdidas if perdidas else "none  <-- SAFE"
    print(f"  classes NOT marked dead that lose their definition: {saude}")
    if avisos:
        print("  custom properties defined only in deleted rules but consumed elsewhere:")
        for v, s in avisos:
            print(f"    {v}  (in: {s})")

    if a.apply:
        novo = re.sub(
            r"\n{4,}", "\n\n\n", "\n".join(l for k, l in enumerate(linhas) if k not in apagar)
        )
        open(a.css, "w", encoding="utf-8").write(novo)
        print(f"\nAPPLIED {a.css}: {n} -> {novo.count(chr(10)) + 1} lines")
    else:
        print("\n(dry-run: nothing written; add --apply)")


if __name__ == "__main__":
    main()
