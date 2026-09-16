---
name: dead-code-elimination
description: Use when pruning dead code, CSS or i18n keys from a repo.
license: MIT
---

# Dead code / dead style elimination

Remove what nothing references, keep everything that is live, and prove both halves. A scan whose only evidence is "no import found" is not enough — the gates below are the difference between a clean pass and a broken UI that nobody notices until much later.

## Order of work

1. Snapshot the source you are about to edit (`cp <file> /tmp/<name>.antes`) so the before/after measurement and review are possible later.
2. Enumerate candidates mechanically: `python3 scripts/dead_scan.py ROOT --css <css> --i18n <dir> --json /tmp/dead.json`.
3. Run every false-positive gate below against every candidate. Gates are cheap; a wrong deletion is not.
4. Apply: `python3 scripts/css_surgery.py <css> /tmp/dead.json` (dry-run) then `--apply`; catalogs per `references/i18n-catalogs.md`.
5. Run the verification checklist. Only then report.

## The search that finds real usage

Search the WHOLE repo — app code, main/electron process, tests, docs, configs — with a true identifier boundary:

```
(?<![\w.-])NAME(?![\w.-])
```

The `-` and `.` inside the lookarounds are mandatory: without them `tile` matches inside `library-tile`, and any `.foo` looks used because `.foo-bar` exists somewhere.

Never restrict the search to `className="..."` or to `from "..."` edges. Usage also arrives through template literals, `classList`, arrays of labels, `data-testid`, string concatenation and string-keyed registries — all of those count as live.

## False-positive gates

Each of these cost real time to discover; run them all.

- **Dynamic import / lazy loading.** A component mounted via `lazy(() => import("..."))`, a route table, or a string-keyed registry has no static import edge, so an import-graph scan reports it dead. Search the bare symbol name repo-wide before calling any component dead.
- **Comments are not usage.** When the only hits are comments or docs, the code really is dead — read the hits instead of trusting the count.
- **Siblings and variants.** BEM files accumulate unused members: the code uses `.glass-1` while the file still defines `.glass-2` / `.glass-3`; uses `.ui-card` while `.ui-card-soft` sits unused. Those members are dead — but only after the next gate passes.
- **Dynamically built class names.** `` className={`family__${part}`} `` keeps every member of the family alive. For each candidate, substring-search the code for the family stem (name before `__`, or the name minus its `--modifier`) and READ the context. Delete only when the context shows a different member spelled literally.
- **Migration / normalization flags are not dead code.** Flags that rewrite old configs to safe values (`*_v2`, `*_v3`, legacy, migrar) are live behavior. Removing them is a behavior change, not a cleanup — leave them and say so in the report.

## CSS surgery rules

- Confirm the file is flat before using line-range deletion: max brace depth 2, and no `@apply` / `@layer` / `@utility`. If it nests, use a real parser instead of `scripts/css_surgery.py`.
- A selector is dead iff it contains AT LEAST ONE dead class — matching requires all classes present, so one dead class poisons the whole selector, including `.live .dead` and `.dead:hover`.
- Never drop a rule that has a mixed selector list. Remove the dead selectors from the comma list and keep the live ones; delete the rule outright only when every selector dies.
- Recurse inside `@media` / `@supports` and drop the conditional block when all its inner rules die.
- `@keyframes`: only after the rules are gone, delete a block whose name is referenced neither in a surviving `animation` / `animation-name` declaration nor anywhere in TS/JS. `animation: "scan 2s linear infinite"` inside a style prop is a real consumer — grep the name in code before touching it.
- **Custom properties:** a dead rule can be the only definition of a var consumed by a live rule. Compare `--x:` definitions inside the deletion region against `var(--x)` occurrences outside it; if a consumer survives, keep the definition or confirm the consumer has a fallback, and report it either way. The consumer is often NOT in the stylesheet: inline `style={{ color: "var(--x)" }}`, an arbitrary Tailwind value (`text-[var(--x)]`, `bg-[var(--x)]/45`) and a component's own `<style>` block all read it from TS/JSX, so a stylesheet-only scan calls it dead and deleting the definition silently blanks the colour (a var with no value is not an error — it just paints nothing). Grep the token NAME across the whole tree (`grep -rn "var(--token" src`) before deleting, and treat a repo ratchet like "every `var(--token)` used has a definition" as the backstop that names the exact file.
- **Run the project's build after any scripted rewrite of the stylesheet** — it is the only reliable detector for the damage a regex pass leaves behind. A CSS parser reports the RULE it could not close (`Missing closing } at .selector`), which points straight at the site; iterate build → fix → build. Two failures worth pre-empting: replacing an `rgba(...)` inside a `linear-gradient(...)` can leave an extra `)` (the replacement string carries its own close while the original's stayed) or drop the gradient's closing paren; and a "remove the whole line" regex eats the `}` of a rule written on one line (`.x { --token: red; }`), which cascades into an unclosed block far below. After the rewrite, compare `(`/`)` per declaration and confirm the compiled output still contains every selector the source defines.
- **Never leave a multi-line comment open.** Line-wise deletion happily removes a comment's continuation lines (`   … .glass-3 has an opaque fallback. */`) while keeping the opening `/*`, and from then on EVERY rule after it is comment text: the source still shows the rules, the CSS compiler silently drops them, and only the built stylesheet reveals it. Comments in the file being pruned are load-bearing — after surgery, scan the file for `/*` with no matching `*/` and for comment bodies that contain a selector, and fix before applying.

## i18n catalogs

See `references/i18n-catalogs.md`. The two non-obvious rules: exclude the catalogs from the search (otherwise every key trivially "exists" and nothing is ever dead), and protect every dynamically assembled key prefix.

## Verification checklist — all of it, before claiming done

- No class referenced in code that was defined in the old CSS lost its definition (parse old/new CSS and diff against the referenced set; the count must be 0). Recompute this yourself from the OLD file and the CURRENT tree — do not reuse the prune script's own summary, and search the whole tree, including components you never opened and platform branches you cannot run.
- The BUILT stylesheet still contains every class the source CSS defines. A rule can survive in the source and still be absent from the output (unbalanced comment, bad escape): compare source-defined selectors against the compiled CSS, and fix the source until they match. `references/pos-prune-verification.md` has the checks ready to run.
- Every class used in runtime JSX is styled somewhere — the compiled CSS, the stylesheet, or a component's inline `<style>` block. Names styled NOWHERE can be deliberate hooks (kept as markers, e.g. targets for user-injected CSS): audit each one and keep the survivors in an explicit, commented allowlist so the check stays green.
- Every dynamically assembled key domain still resolves: derive it from the union/type that enumerates it and from the literals the main process returns, then assert each key exists in every catalog (see `references/i18n-catalogs.md`).
- No class referenced in code that was defined in the old CSS lost its definition (parse old/new CSS and diff against the referenced set; the count must be 0).
- No animation name used in surviving CSS or in code lost its `@keyframes`.
- Braces balanced, zero empty rules, no section header left with no rules under it.
- The project's gates pass in its own CI order (tests → typecheck → build).
- Leave the checks in the repo as tests, not just in this session's transcript: a comment-integrity guard, a source-vs-compiled CSS guard, and a dynamic-i18n-key guard. They run in milliseconds and catch precisely the mistakes a text-based scan makes.
- Shipped artifact measured before/after: temporarily restore the saved old source, build, record the size, restore the new source, rebuild, and check the file hash matches what you had before. This is what turns "deleted 2k lines" into "the shipped bundle dropped N KB".

## Reporting

Report counts per category (lines, classes, keys, bytes) and name the gates that passed. If a gate found something, say what stayed and why. Never present a removal as verified without the checklist above.
