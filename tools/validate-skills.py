#!/usr/bin/env python3
"""Validate every bundled skill against the Agent Skills spec.

Checks (https://agentskills.io/specification):
  - SKILL.md exists in each skill dir and starts with '---' at byte 0
  - frontmatter parses as YAML and has name + description
  - name matches the directory name and the ^[a-z0-9]+(-[a-z0-9]+)*$ rule
  - description is 1..1024 chars
  - no machine-local absolute paths (/home/<user>/...) baked into the files

Usage:  python3 tools/validate-skills.py [--quiet]
Exit code 0 = all good, 1 = problems found.
"""
import os, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LOCAL_PATH_RE = re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+/")
# /home/user, /Users/me, /home/<voce>... são exemplos de doc, não caminho de máquina
PLACEHOLDER_USERS = {"user", "users", "me", "you", "youruser", "username", "usuario",
                     "<user>", "<voce>", "example", "someone", "your-name"}

def frontmatter(text):
    """Return (mapping, body) or (None, None) when the file is malformed."""
    if not text.startswith("---"):
        return None, None
    m = re.search(r"\n---\s*\n", text[3:])
    if not m:
        return None, None
    raw = text[3:m.start() + 3]
    body = text[m.end() + 3:]
    try:
        import yaml
        data = yaml.safe_load(raw)
    except ImportError:
        data = None
        for line in raw.splitlines():
            km = re.match(r'^([A-Za-z0-9_-]+):\s*(.*)$', line)
            if km:
                data = data or {}
                data[km.group(1)] = km.group(2).strip().strip('"\'')
            elif data is not None and line.startswith(("  ", "\t")) and data:
                last = list(data)[-1]
                data[last] = (str(data[last]) + " " + line.strip()).strip()
    if not isinstance(data, dict):
        return None, None
    return data, body

def main():
    quiet = "--quiet" in sys.argv
    errors, warns, count = [], [], 0
    seen = {}
    for dirpath, dirnames, filenames in os.walk(SKILLS):
        if "SKILL.md" not in filenames:
            continue
        count += 1
        d = pathlib.Path(dirpath)
        name = d.name
        rel = d.relative_to(ROOT)
        text = (d / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        fm, body = frontmatter(text)
        if fm is None:
            errors.append(f"{rel}: frontmatter invalido ou ausente")
            continue
        fname = str(fm.get("name", "")).strip()
        desc = str(fm.get("description", "")).strip()
        if not fname:
            errors.append(f"{rel}: sem campo 'name'")
        elif fname != name:
            errors.append(f"{rel}: name='{fname}' != diretorio '{name}'")
        elif not NAME_RE.match(fname):
            errors.append(f"{rel}: name fora do padrao {NAME_RE.pattern}")
        if not desc:
            errors.append(f"{rel}: sem campo 'description' (body {len(body)} chars)")
        elif len(desc) > 1024:
            errors.append(f"{rel}: description com {len(desc)} chars (>1024)")
        if not body.strip():
            errors.append(f"{rel}: corpo vazio depois do frontmatter")
        if not fm.get("license"):
            warns.append(f"{rel}: sem campo 'license'")
        for f in d.rglob("*"):
            if f.is_file() and f.suffix in (".md", ".sh", ".py", ".js", ".json", ".yaml", ".yml", ".toml"):
                try:
                    t = f.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                for i in LOCAL_PATH_RE.finditer(t):
                    if i.group(0).split("/")[2].lower() not in PLACEHOLDER_USERS:
                        warns.append(f"{f.relative_to(ROOT)}: caminho de maquina local '{i.group(0)}'")
                        break
        seen.setdefault(name, []).append(str(rel))
    dup = {k: v for k, v in seen.items() if len(v) > 1}
    for k, v in dup.items():
        errors.append(f"nome duplicado '{k}': {v}")

    print(f"skills verificadas: {count}")
    print(f"erros: {len(errors)}   avisos: {len(warns)}")
    if not quiet:
        for e in errors:
            print(f"  ERRO  {e}")
        for w in warns[:40]:
            print(f"  AVISO {w}")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
