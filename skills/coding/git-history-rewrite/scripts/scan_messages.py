#!/usr/bin/env python3
"""Inventario de mensagens antes de reescrever historico.

Uso: scan_messages.py <repo> [ref] [outdir]

Escreve em outdir (default /tmp/history-scan): messages.tsv (hash, data, sujeito,
corpo escapado), noprefix.tsv, monster.tsv, forbidden.tsv, identities.txt.
Imprime so o resumo - nunca despeje o log inteiro no terminal: saida longa de
ferramenta e truncada em silencio e voce subconta sem perceber.

Lista extra de termos: aponte FORBIDDEN_FILE=<caminho> com um termo por linha.
"""
import collections
import os
import pathlib
import re
import subprocess
import sys

FORBIDDEN = [
    "crack", "bypass", "keygen", "warez", "repack", "fitgirl", "skidrow",
    "empress", "elamigos", "steamrip", "denuvo", "drm", "unlock", "desbloque",
    "pirat", "cracked games", "online fix", "goldberg", "hydra",
    "claude", "codex", "opencode", "hermes agent", "copilot",
]
CONV = re.compile(r"^(feat|fix|chore|refactor|docs|test|perf|style|ci|build|revert)(\(|!|:)")
FOOTER = re.compile(r"^(co-authored-by|generated with|assisted-by|\U0001f916)", re.I | re.M)
MONSTER_LEN = 100


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout


def termos():
    extra = os.environ.get("FORBIDDEN_FILE")
    lista = list(FORBIDDEN)
    if extra and pathlib.Path(extra).is_file():
        lista += [l.strip().lower() for l in pathlib.Path(extra).read_text().splitlines() if l.strip()]
    return lista


def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    ref = sys.argv[2] if len(sys.argv) > 2 else "master"
    out = pathlib.Path(sys.argv[3] if len(sys.argv) > 3 else "/tmp/history-scan")
    out.mkdir(parents=True, exist_ok=True)
    raw = git(repo, "log", "--format=%H%x1f%ad%x1f%an%x1f%ae%x1f%s%x1f%b%x1e", "--date=short", ref)
    commits = []
    for blk in raw.split("\x1e"):
        p = blk.strip("\n").split("\x1f")
        if len(p) >= 6:
            commits.append({"h": p[0], "d": p[1], "an": p[2], "ae": p[3], "s": p[4], "b": p[5]})
    ban = termos()
    with open(out / "messages.tsv", "w", encoding="utf-8") as f:
        for c in commits:
            corpo = c["b"].replace("\n", " \\n ")
            f.write(c["h"] + "\t" + c["d"] + "\t" + c["s"] + "\t" + corpo + "\n")
    nopref = [c for c in commits if not CONV.match(c["s"]) and not c["s"].lower().startswith("merge")]
    monster = [c for c in commits if len(c["s"]) > MONSTER_LEN]
    foot = [c for c in commits if FOOTER.search(c["b"])]
    hits = {}
    for c in commits:
        txt = (c["s"] + " " + c["b"]).lower()
        achados = [t for t in ban if t in txt]
        if achados:
            hits[c["h"]] = achados
    for nome, dados in (("noprefix.tsv", nopref), ("monster.tsv", monster),
                        ("forbidden.tsv", [c for c in commits if c["h"] in hits])):
        with open(out / nome, "w", encoding="utf-8") as f:
            for c in dados:
                extra = ",".join(hits.get(c["h"], [])) if nome == "forbidden.tsv" else str(len(c["s"]))
                corpo = c["b"].replace("\n", " \\n ")
                f.write(c["h"] + "\t" + c["d"] + "\t" + c["s"] + "\t" + extra + "\t" + corpo + "\n")
    ident = collections.Counter(c["an"] + " <" + c["ae"] + ">" for c in commits)
    (out / "identities.txt").write_text("\n".join(f"{n:5d} {k}" for k, n in ident.most_common()) + "\n", encoding="utf-8")
    merges = sum(1 for c in commits if c["s"].lower().startswith("merge"))
    print(f"commits em {ref}: {len(commits)} | merges: {merges}")
    for k, n in ident.most_common():
        print(f"  identidade: {n:5d} {k}")
    print(f"  sem prefixo conventional: {len(nopref)}")
    print(f"  sujeito > {MONSTER_LEN} chars: {len(monster)}")
    print(f"  rodape de agente/IA: {len(foot)}")
    print(f"  com termo da lista ({len(ban)} termos): {len(hits)}")
    print(f"listas em {out}")


if __name__ == "__main__":
    main()
