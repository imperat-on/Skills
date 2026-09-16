# i18n catalog pruning

Catalogs are usually one key per line, sorted, with identical key sets across locales. Prune them line-wise; never re-serialize the whole file (that reorders, re-escapes and produces an unreviewable diff).

## Procedure

1. Get the dead-key list from `scripts/dead_scan.py` (section 5).
2. For each catalog, drop the lines whose key matches `^\s*"<key>":\s`.
3. Fix JSON validity: when the LAST entry was removed, the previous line is left with a trailing comma before the closing brace. Walk back from the final `}`, find the last non-blank line, strip a trailing `,`.
4. Validate with `json.loads` on the resulting text (not on the file path, so a failed write cannot hide the error) and print before → after key counts.
5. Assert all locale catalogs still have IDENTICAL key sets, and that no removed key survives.

## Two rules that decide correctness

- **Exclude the catalog files from the reference search.** Searching the whole repo including the catalogs means every defined key is "found" (in its own file) and nothing is ever classified dead. Pass the catalog paths as skips.
- **Protect dynamically assembled keys.** Keys can be built at runtime three ways:
  - ``t(`prefix.${value}`)`` — collect the literal before `${` as a protected prefix;
  - `t("prefix." + value)` — same;
  - `t(variable)` where the variable comes from a data structure (`labelKey`, `descKey`, `badgeKey`) or an external manifest (plugin definitions, server payloads).

  For the first two, keep every defined key that starts with a collected prefix. For the third, note that the structure's string literals live IN the repo, so the plain repo-wide search already finds them — but keys supplied by an external manifest (a plugin manifest read at runtime, a payload from the backend) cannot be found statically. Check whether such a source exists before deleting keys in its namespace; if it does, either leave that namespace alone or confirm the literal exists somewhere in the repo.

## Sanity checks

- A used-but-undefined key renders as a raw string in the UI. After pruning, re-run the reference check for every key you removed; a hit means the gate was wrong.
- Spot-check three removed keys with a raw `grep -F` over the repo before applying — it catches a broken boundary regex immediately.
