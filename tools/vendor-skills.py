#!/usr/bin/env python3
"""Vendoriza skills de um clone local para dentro do kit e atualiza os metadados.

Uso:
    python3 tools/vendor-skills.py --plan          # mostra o que faria
    python3 tools/vendor-skills.py                 # copia e atualiza tudo

Por que existe: os scripts de build originais viviam em /tmp e sumiram quando o
/tmp foi limpo no meio do trabalho. Este arquivo mora no repo, tem os hashes e
regenera CATALOG.md + SOURCES.md a partir do manifest.json.

Edite a lista SOURCES/PLAN abaixo ao adicionar uma origem nova.
    copy path -> nome do diretório do clone (relativo à raiz do clone externo)
    name      -> nome exato do diretório da skill dentro de copy path
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil

REPO = pathlib.Path(__file__).resolve().parent.parent
CLONES = pathlib.Path("/tmp/src")
MANIFEST = REPO / "manifest.json"

# ---------------------------------------------------------------- origens ----
# stars e last_push conferidos com `gh api repos/<repo>` em 2026-09-16/17
SOURCES = {
    "superpowers": dict(url="https://github.com/obra/superpowers", stars=287594, push="2026-09-14",
                        license="MIT", author="Jesse Vincent (obra)",
                        path="superpowers/skills"),
    "ecc": dict(url="https://github.com/affaan-m/ECC", stars=260098, push="2026-09-15",
                license="MIT", author="Affaan Mustafa (affaan-m)", path="ECC/skills"),
    "wshobson-agents": dict(url="https://github.com/wshobson/agents", stars=39729, push="2026-09-14",
                            license="MIT", author="Seth Hobson (wshobson)", path="agents/plugins"),
    "anthropic-skills": dict(url="https://github.com/anthropics/skills", stars=176699, push="2026-09-10",
                             license="Apache-2.0", author="Anthropic", path="skills/skills"),
    "bmad": dict(url="https://github.com/bmad-code-org/BMAD-METHOD", stars=53104, push="2026-09-16",
                 license="MIT", author="BMad Code, LLC", path="BMAD-METHOD/skills"),
    "vercel-labs": dict(url="https://github.com/vercel-labs/agent-skills", stars=31248, push="2026-08-28",
                        license="MIT", author="Vercel Labs", path="agent-skills/skills"),
    "worktrunk": dict(url="https://github.com/max-sixty/worktrunk", stars=7910, push="2026-09-16",
                      license="MIT OR Apache-2.0", author="Max Sixty (max-sixty)", path="worktrunk/skills"),
    "caveman": dict(url="https://github.com/JuliusBrussee/caveman", stars=106123, push="2026-09-16",
                    license="MIT", author="Julius Brussee (JuliusBrussee)", path="caveman/skills"),
    "token-optimizer": dict(url="https://github.com/KINGSTAR-OMEGA/claude-token-optimizer", stars=121,
                            push="2026-04-12", license="MIT", author="KINGSTAR-OMEGA",
                            path="claude-token-optimizer"),
}

# (categoria, tier, origem, nome da skill no clone)
PLAN = [
    ("efficiency", "core", "caveman", "caveman"),
    ("efficiency", "extra", "caveman", "caveman-compress"),
    ("efficiency", "extra", "caveman", "caveman-review"),
    ("efficiency", "extra", "caveman", "caveman-commit"),
    ("efficiency", "extra", "caveman", "caveman-explore"),
    ("efficiency", "extra", "caveman", "caveman-help"),
    ("efficiency", "extra", "caveman", "cavecrew"),
    ("efficiency", "extra", "caveman", "lean-build"),
    ("efficiency", "extra", "caveman", "investigate-first"),
    ("efficiency", "extra", "token-optimizer", "antigravity2.0"),
    ("efficiency", "extra", "token-optimizer", "ultimate-protocol"),
]

CAT_TITLE = {"coding": "Codificação", "thinking": "Pensamento e planejamento",
             "teams": "Trabalho em grupo (subagentes)", "frontend": "Frontend e UI",
             "orchestration": "Orquestração de agentes", "efficiency": "Economia de token"}
LOCAL_LABEL = "local (skill pessoal, herdada de ~/.hermes/skills)"


def sha(p, n=16):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:n]


def frontmatter_name(text):
    m = re.search(r"^name:\s*(.+)$", text, re.M)
    return m.group(1).strip().strip("\"'") if m else None


def add_license(md, lic):
    t = pathlib.Path(md).read_text(encoding="utf-8")
    m = re.search(r"\n---\s*\n", t[3:])
    if not m or re.search(r"^license:", t[3:m.start() + 3], re.M):
        return False
    cut = 3 + m.start() + 1
    pathlib.Path(md).write_text(t[:cut] + f"license: {lic}\n" + t[cut:], encoding="utf-8")
    return True


def find_skill_dir(srcpath, name):
    """O nome pode estar no diretório ou no frontmatter (ex.: antigravity2.0)."""
    hits = [p for p in pathlib.Path(srcpath).rglob("SKILL.md")
            if p.parent.name == name and "/.git/" not in str(p)]
    if not hits:
        for p in pathlib.Path(srcpath).rglob("SKILL.md"):
            if "/.git/" in str(p):
                continue
            if frontmatter_name(p.read_text(encoding="utf-8", errors="replace")) == name:
                hits.append(p)
                break
    return hits[0].parent if hits else None


def vendor(plan, dry=False):
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    have = {s["name"] for s in man["skills"]}
    added, skipped = [], []
    for cat, tier, src_key, name in plan:
        src = SOURCES[src_key]
        d = find_skill_dir(CLONES / src["path"], name)
        if d is None:
            skipped.append((name, "não achei no clone"))
            continue
        md = d / "SKILL.md"
        real = frontmatter_name(md.read_text(encoding="utf-8", errors="replace")) or d.name
        if real in have:
            skipped.append((real, "já está no kit"))
            continue
        dst = REPO / "skills" / cat / real
        if dry:
            print(f"  + skills/{cat}/{real}  ({tier}, {src_key})")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(d, dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        add_license(dst / "SKILL.md", src["license"])
        man["skills"].append(dict(
            name=real, category=cat, tier=tier, license=src["license"], author=src["author"],
            source=src["url"],
            upstream_path=str(d.relative_to(CLONES)) + "/SKILL.md",
            upstream_sha256=sha(md), bundled_sha256=sha(dst / "SKILL.md"),
            lines=(dst / "SKILL.md").read_text(encoding="utf-8").count("\n") + 1,
            files=sum(len(f) for _, _, f in os.walk(dst))))
        have.add(real)
        added.append(real)
    if not dry:
        man["skills"].sort(key=lambda s: (s["category"], s["tier"] != "core", s["name"]))
        man["count"] = len(man["skills"])
        MANIFEST.write_text(json.dumps(man, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return man, added, skipped


def write_catalog(man):
    sk = man["skills"]
    L = ["# Catálogo de skills", "",
         f"{len(sk)} skills, todas verificadas contra a spec Agent Skills "
         "(`python3 tools/validate-skills.py`).", "",
         "**core** = instalada por padrão (`install.sh`). **extra** = só com `--tier all` "
         "(mantém a lista inicial curta: o Codex corta descrições quando há muitas skills).", ""]
    for cat, title in CAT_TITLE.items():
        rows = [s for s in sk if s["category"] == cat]
        if not rows:
            continue
        L += [f"## {title} — {len(rows)} skills", "", "| skill | tier | linhas | origem | licença | o que faz |",
              "|---|---|---|---|---|---|"]
        for r in rows:
            t = (REPO / "skills" / cat / r["name"] / "SKILL.md").read_text(encoding="utf-8", errors="replace")
            m = re.search(r"^description:\s*(.*)$", t, re.M)
            d = m.group(1).strip().strip("\"'") if m else ""
            if d in (">", "|", ">-", "|-"):
                m2 = re.search(r"^description:\s*[>|][+-]?[ \t]*\n((?:[ \t]+.*\n)+)", t, re.M)
                d = " ".join(x.strip() for x in m2.group(1).split()) if m2 else ""
            short = r["source"].replace("https://github.com/", "")
            L.append(f'| `{r["name"]}` | {r["tier"]} | {r["lines"]} | {short} | {r["license"]} | {d[:150]} |')
        L.append("")
    deps = (REPO / "tools" / "external-deps.md")
    L.append(deps.read_text(encoding="utf-8") if deps.exists() else "")
    (REPO / "CATALOG.md").write_text("\n".join(L), encoding="utf-8")


def write_sources(man):
    sk = man["skills"]
    def key(src):
        if src.startswith("https://github.com/"):
            return src.replace("https://github.com/", "")
        return "local"
    import collections
    by = collections.defaultdict(list)
    for s in sk:
        by[key(s["source"])].append(s)
    lookup = {v["url"].replace("https://github.com/", ""): v for v in SOURCES.values()}
    L = ["# Origens, licenças e créditos", "",
         "Números medidos nesta máquina com a API do GitHub autenticada e clones "
         "`--depth 1` (2026-09-16/17). Onde não deu para medir, está escrito.", "",
         "| Fonte | Estrelas | Licença | Skills usadas | Último push |", "|---|---|---|---|---|"]
    for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
        if k == "local":
            L.append(f"| `~/.hermes/skills` (skills pessoais do autor) | — | MIT | {len(v)} | — |")
            continue
        meta = lookup.get(k, {})
        L.append(f"| [{k}](https://github.com/{k}) | {meta.get('stars','?')} | "
                 f"{meta.get('license','?')} | {len(v)} | {meta.get('push','?')} |")
    L += ["", f"Total: **{len(sk)} skills**, {sum(s['lines'] for s in sk)} linhas de `SKILL.md`.", "",
          "## Crédito por skill", "", "| Skill | Categoria | Tier | Origem | Licença | Linhas |",
          "|---|---|---|---|---|---|"]
    for s in sk:
        k = key(s["source"])
        origin = "skills pessoais do autor" if k == "local" else f"[{k}]({s['source']})"
        L.append(f'| `{s["name"]}` | {s["category"]} | {s["tier"]} | {origin} | {s["license"]} | {s["lines"]} |')
    L += ["", "Hash do arquivo original de cada skill: `manifest.json` "
          "(`upstream_sha256`). A única edição feita nos arquivos é o campo `license:` "
          "quando o original não trazia.", ""]
    (REPO / "SOURCES.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    a = ap.parse_args()
    man, added, skipped = vendor(PLAN, dry=a.plan)
    print(f"adicionadas: {len(added)}  puladas: {len(skipped)}")
    for n, why in skipped:
        print(f"  . {n}: {why}")
    if not a.plan:
        write_catalog(man)
        write_sources(man)
        print(f"manifest: {man['count']} skills | CATALOG.md e SOURCES.md regerados")
