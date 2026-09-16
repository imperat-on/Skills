---
name: git-history-rewrite
description: Use when rewriting git history (messages, authors).
license: MIT
---

# Rewriting git history

Triggers: "make the commit history professional", scrubbing a public repo of
wording that invites legal trouble, unifying several author identities, fixing a
branch full of monster subjects, moving tags and releases after a rewrite.

A rewrite changes every hash. Treat it as destructive and irreversible on the
remote, and as cheap and repeatable locally.

## 1. Recon, read-only, written to files

- Scope to the branch that is actually public: `git ls-remote --heads origin`,
  `git rev-list --count <branch>`, `gh repo view --json
  isPrivate,forkCount,visibility`. Local leftovers (`ao/*`-style worktree
  branches) do not count.
- Inventory identities: `git log --format='%an <%ae>' | sort | uniq -c`. Three
  identities in one history is the normal case, not an oddity.
- Inventory tags and releases BEFORE deciding: every annotated tag must be
  recreated and every release hanging off a tag has to be re-pointed.
- **Write bulk git output to a file and summarize with Python; never print a
  500-line log into a tool result.** Long tool output is truncated silently and
  you will undercount without noticing (a 481-commit log that parses as 143
  records is the failure shape). Print counts, hashes and samples only.
- `scripts/scan_messages.py <repo> [ref] [outdir]` does the whole inventory:
  totals, merges, identities, commits hitting forbidden tokens, subjects without
  a conventional prefix, monster subjects, agent footers.

## 2. Policy in writing, before touching anything

Copy `templates/message-policy.md`, fill it in (language, allowed types, the
forbidden-term list with its substitution for each, legitimate third-party tool
names that stay, footer rules, body rules) and keep it on disk: it is the
contract you hand to the message rewriters and the checklist you validate with.

Separate two classes of term, or you will damage good prose:

- **Hard-banned**: DRM-circumvention and piracy-tool wording (crack family,
  bypass, unlock of paid content, DRM/denuvo, overlay plugins and their config
  directories, service/group/forum names) plus agent names and footers.
- **Context-dependent**: words for a legitimate product feature (an achievement
  unlocking, a download engine, a catalog concept). Ban them only inside the
  phrase that promises the illicit thing.

Also state the honest limit in the final report: rewriting text does not remove
the capability from the code. It is a public-reading fix; the real fixes are
making the repo private or dropping the feature.

## 3. Rewrite in a MIRROR clone

```
uv tool install git-filter-repo                       # or uvx
cp -r mirror.git attempt.git                          # the attempt mutates the clone
cd attempt.git && git filter-repo --force --refs master \
     --commit-callback "$(cat body.py)"
```

- Keep one pristine mirror (`git clone --mirror <repo>`) as the source of truth
  and copy it per attempt: a full rewrite of hundreds of commits takes seconds,
  so iterate by re-running, never by hand-patching a rewritten repo.
- `--refs <branch>` bounds the job to the public branch; other local branches
  keep the old wording but never reach the remote.

### The callback is a function BODY, not a definition

`--commit-callback` takes Python statements executed once per commit (merges
included) with `commit` in scope. A file containing `def callback(commit): ...`
declares an unused function, runs once, and **exits 0 having changed nothing** —
a silent no-op that looks exactly like success. Ship the logic as an importable
module and pass a three-line body:

```python
import sys
sys.path.insert(0, '/tmp/rw')
import rw_apply
rw_apply.run(commit)
```

Inside, `commit.original_id` is the original SHA as **bytes**, `commit.message`
is bytes, and identity is set with `commit.author_name/author_email` and
`commit.committer_name/committer_email` (bytes). Assigning those unifies
identities without a `--mailmap`.

### Maps keyed by hash, and the positional conversion

- Key message overrides by `original_id` (the pre-rewrite SHA).
- Maps produced *after* a first pass are keyed by the NEW hashes. Convert by
  position: count and order are preserved, so `zip()` the two `git log
  --format=%H` lists (verify first that the `%T` sequences match pairwise). Do
  not hunt for a commit-map file; it is not reliably written.
- One consolidated map beats layered precedence rules. Build it once with an
  explicit priority order (manual fixes > structural rewrites > translations >
  term rewrites > prefix normalization).

## 4. Verify at tree level, not by eye

`git log --format=%T` on old and new must be **identical line for line**: same
count, same order, same tree hashes, which proves file content is byte-for-byte
preserved and only metadata changed. Then assert: no forbidden term anywhere,
every subject matches the conventional regex, no empty messages, exactly one
identity, and the date sequences (`%aI|%cI`) unchanged.

`scripts/verify_history_rewrite.py <old-repo> <new-repo> [ref]` runs all of it
and exits non-zero on any failure.

## 5. Swap the local repo without losing uncommitted work

1. Back up first: `git diff > wip.patch` plus copies of the modified files.
2. `git stash push` -> `git reset --hard <new-sha>` -> `git stash pop`. The trees
   are identical, so the stash reapplies cleanly and the dirty files survive.
3. **Rehearse the whole sequence in a copy of the working repo** (rsync out
   `node_modules/`, `dist/`, build output) and compare `git diff` before and
   after: they must be byte-identical. Then do it for real.

## 6. Tags, releases, and the push

- Recreate the annotated tag on the new commit with the unified tagger; the old
  tag points at the commit you just abandoned. Push order: force-push the branch,
  delete the remote tag, push the new tag. A GitHub release attached to the tag
  NAME survives that swap and re-attaches to the new tag.
- Say what changes for the user: every hash changes, other clones and forks must
  be re-cloned, saved references to old SHAs stop resolving.
- **A force-push to a public branch needs the user's explicit go-ahead in this
  session.** The terminal's destructive-command gate blocks it; a block is
  missing consent, not a failed command. Do not retry it, do not rephrase it,
  and do not reach the same outcome another way: report what is staged (with
  hashes) and stop. Re-running it later, after the user says go, is a fresh
  action and is fine.

## 7. Bulk message rewriting: delegate the volume, validate the output

Hand the mechanical volume to subagents, one JSON output per class: prefix
normalization, forbidden-term rewrites, translations, monster-subject splitting.
Give each the policy file on disk and require a fixed key set plus a self-run
validator.

Never trust the self-report. Validate programmatically: key set identical to the
input hashes (no missing, no extra), every subject matching the conventional
regex, no forbidden term in subject or body, bodies that existed still non-empty
and no shorter than the original, bullet counts preserved (structure loss shows
up as fewer `\n- `), no agent footer, length ceilings respected.

Split monster subjects losslessly: a concise subject (<= ~90 chars) plus the
descriptive remainder promoted to the first body paragraph. Detail then survives
the rewrite instead of being dropped.

## 8. After the push: branches, and the user's own clone

- **Never bulk-delete branches.** For each local branch, count the patches that
exist nowhere else: `git cherry <old-tip> <branch> | grep -c '^+'`. Delete only
the ones with zero (pure leftovers, often an orchestrator's empty recreations),
and report the counts for the rest — a branch with a single unique patch can be
unreviewed work. Prune stale worktree metadata first (`git worktree prune`); a
branch checked out in a LIVE worktree is not yours to delete.
- Keep the pre-rewrite history reachable locally before deleting its refs:
`git branch backup/pre-rewrite-<short-old-tip> <old-tip>` (local only, never
pushed) and hand the user the one command that drops it.
- **Expect the user to re-clone to pick up the rewrite, and say in the same
message that a re-clone discards uncommitted work.** Their clone is the point of
the exercise; their WIP is the casualty. Keep the WIP backup patch and copies of
the modified files outside the repo until the clone has happened.
- A clean tree where you expected dirty files is usually a re-clone, not data
loss: `git reflog` shows a single `HEAD@{...}: clone: from <url>` entry. Restore
with `git apply --check <patch>` -> `git apply <patch>` -> verify the resulting
`git diff` is byte-identical to the backup (`diff -q`). A fresh clone also has no
installed dependencies: if the suite suddenly reports module-not-found failures
across many files, that is the install step, not your commit.

## Pitfalls

- A safety-net regex must run ONLY over messages that no map covers. Run it over
  approved prose and it mangles real identifiers (`localUnlock` ->
  "localLiberacoes") - the tell is a rewritten word inside a code span.
- Neutralizing a term inside a message can name a symbol the code does not have
  (a renamed function or file). Acceptable when the symbol itself is the problem,
  but say it in the report so nobody greps for a name that does not exist.
- Term lists age. Once you decide to scrub, scan with a WIDE token list - tool
  names, service names, plugin config directories, group and forum names, version
  numbers - because the obvious words are the ones already caught.
- Published release assets are immutable history: if the bytes must change, bump
  the patch version and publish a new release rather than reusing the number,
  otherwise "which build am I running?" becomes unanswerable. When the user asks
  to replace what is in the releases page, that means a new version plus removing
  the superseded release (keep its git tag).
- Removing images or sections from a README does not remove the asset files from
  the repo; leave them and mention their size rather than deleting on your own.
