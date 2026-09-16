#!/usr/bin/env python3
"""Verifica uma reescrita de historico comparando arvores, datas e mensagens.

Uso: verify_history_rewrite.py <repo_original> <repo_reescrito> [ref]

Fecha com exit 1 se qualquer invariante falhar. A checagem que importa e a
sequencia de %T: identica na mesma ordem = conteudo dos arquivos preservado byte
a byte, so metadados mudaram.

Lista extra de termos proibidos: FORBIDDEN_FILE=<caminho>, um por linha.
"""
import os
import pathlib
import re
import subprocess
import sys

FORBIDDEN = [
    "crack", "bypass", "keygen", "warez", "repack", "fitgirl", "skidrow",
    "empress", "elamigos", "steamrip", "denuvo", "drm", "unlock", "desbloque",
    "pirat", "online fix", "goldberg", "hydra",
    "claude", "codex", "opencode", "hermes agent", "copilot",
]
CONV = re.compile(
    r"^(feat|fix|chore|refactor|docs|test|perf|style|ci|build|revert)(\([a-z0-9-]+\))?!?: .+"
)


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout


def linha_seq(repo, ref, fmt):
    return git(repo, "log", f"--format={fmt}", ref).strip("\n").split("\n")


def mensagens(repo, ref):
    raw = git(repo, "log", "--format=%H%x1f%s%x1f%b%x1e", ref)
    out = []
    for blk in raw.split("\x1e"):
        p = blk.strip("\n").split("\x1f")
        if len(p) >= 3:
            out.append({"h": p[0], "s": p[1], "b": p[2]})
    return out


def proibidos():
    extra = os.environ.get("FORBIDDEN_FILE")
    lista = list(FORBIDDEN)
    if extra and pathlib.Path(extra).is_file():
        lista += [l.strip().lower() for l in pathlib.Path(extra).read_text().splitlines() if l.strip()]
    return lista


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    orig, novo = sys.argv[1], sys.argv[2]
    ref = sys.argv[3] if len(sys.argv) > 3 else "master"
    falhas = []

    def falha(msg):
        falhas.append(msg)
        print(f"  FALHA: {msg}")

    ta, tb = linha_seq(orig, ref, "%T"), linha_seq(novo, ref, "%T")
    print(f"commits: original={len(ta)} reescrito={len(tb)}")
    if len(ta) != len(tb):
        falha("contagem de commits diferente")
    elif ta == tb:
        print("arvores: IDENTICAS na mesma ordem (conteudo preservado byte a byte)")
    else:
        dif = [i for i, (x, y) in enumerate(zip(ta, tb)) if x != y]
        falha(f"sequencia de arvores difere em {len(dif)} posicoes: {dif[:5]}")

    datas_orig = linha_seq(orig, ref, "%aI|%cI")
    if linha_seq(novo, ref, "%aI|%cI") != datas_orig:
        falha("datas de autor/committer mudaram")
    else:
        print("datas: identicas")

    msgs = mensagens(novo, ref)
    ban = proibidos()
    ruins = [m for m in msgs if any(t in (m["s"] + " " + m["b"]).lower() for t in ban)]
    print(f"mensagens com termo proibido ({len(ban)} termos): {len(ruins)}")
    for m in ruins[:10]:
        print("   !", m["h"][:8], m["s"][:90])
    if ruins:
        falha(f"{len(ruins)} mensagens com termo proibido")

    fora = [m for m in msgs if not CONV.match(m["s"]) and not m["s"].startswith("Merge ")]
    print(f"sujeitos fora do padrao: {len(fora)}")
    for m in fora[:10]:
        print("   ?", m["h"][:8], m["s"][:90])
    if fora:
        falha(f"{len(fora)} sujeitos fora do padrao conventional")

    vazias = [m for m in msgs if not m["s"].strip()]
    if vazias:
        falha(f"{len(vazias)} mensagens vazias")

    aut = set(linha_seq(novo, ref, "%an <%ae>")) | set(linha_seq(novo, ref, "%cn <%ce>"))
    print(f"identidades no reescrito: {sorted(aut)}")
    if len(aut) > 1:
        falha("mais de uma identidade no historico reescrito")

    print("RESULTADO:", "OK" if not falhas else f"{len(falhas)} falha(s)")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
