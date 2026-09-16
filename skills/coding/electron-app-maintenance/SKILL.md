---
name: electron-app-maintenance
description: Use when building or debugging an Electron desktop app.
license: MIT
---

# Electron desktop app: build, verify, debug

Applies to local-first desktop apps (Electron + own backend): producing the installer/AppImage, proving the artifact carries your change, and diagnosing runtime state without guessing. Probe template: `templates/electron-probe.js`.

## Packaging

1. Read the packaging script from the project manifest and use it verbatim (`dist:appimage`, `dist:nsis`, …). It normally chains the frontend build, so hand-rolling an `electron-builder` invocation silently ships a stale bundle. Output goes to the configured `build.directories.output`.
2. **Verify the artifact contains your change before reporting success.** Extract it and read the packaged sources:

   ```
   ./Distro-x.y.z-x86_64.AppImage --appimage-extract    # -> squashfs-root/
   grep -n '<symbol you just added>' squashfs-root/resources/app/<path>
   ```

   A clean build log is not evidence: a stale `dist/`, a changed file glob or asar packing will happily publish the old code.
3. Report the `sha256sum` of what you produced, and state that the artifact name comes from the manifest version — two builds of the same version are indistinguishable by name.
4. **Replacing a binary that is currently running:** `cp` over it fails with `Text file busy` (ETXTBSY) because the loader keeps the file open. `mv` the old file aside, then `cp` the new one into the path; the running process keeps its old inode and the path serves the new build. Keep the old file as a `.bak`, and tell the user the process still in their taskbar is the OLD code until they restart.

## Debugging runtime state

1. **Read the app's real data first.** Locate the data dir per platform, then look for per-account subdirectories (`<datadir>/contas/<user>/`), a logs dir, and legacy root-level files. Older versions wrote to the root and newer ones per account: a missing file at the root path is often just the old layout, not a bug. Check which module WRITES a path before declaring its reader wrong.
2. **Query the app's own backend without touching credentials.** Write a temporary probe as an Electron main script INSIDE the app directory (so the app name matches the OS-keyring entry the session was encrypted with), have it require the app's own client/session modules, decrypt the stored session with the app's own loader, call the RPC and print only counts/ids. Copy `templates/electron-probe.js`, run `npx electron .probe.js`, then delete it. Running an equivalent script from outside the app dir can break the keyring lookup and lose the session.
3. **Reproduce on an isolated copy before changing code.** Copy the account dir to a temp dir, point the app's data-dir env var at it, and drive the real code paths. Neutralize outbound writes by overwriting the push/schedule functions on the required module object (same require cache) so nothing reaches the server. Then verify before → after, not just the operation in isolation.
4. **For sync/refresh bugs, reproduce the LOAD ORDER, not the operation.** A function that rebuilds a list from a local index will drop records that arrived from the remote and are missing from that index: the data flows in, renders briefly, and disappears on the next load. Test `pull → reload`, which is the sequence the app actually runs at boot.
5. **Separate "source of truth is local" from "the remote is wrong".** Per-machine stores (emulator/crack save files, per-prefix saves, local caches with no cloud) never travel between machines — no sync layer can fix that. Confirm whether the data is local-only before blaming sync.
6. **Do not state a path/naming bug from reading code alone.** Grep for the writer first; a reader that looks wrong may be intentional by design, and retracting a confident claim costs more than the check.

## Clicks that do nothing

Two causes account for most "I click and nothing happens" reports in an
Electron + React shell, and neither shows up in a build or a unit test:

- **A frameless window's drag regions swallow clicks.** With
  `-webkit-app-region: drag` on the app shell, every descendant becomes a
  window-drag handle unless it escapes with `no-drag`: keep one CSS list of
  escapes (`button`, `a`, `input`, `select`, `textarea`, `video`, `img`,
  `[role="button"]`, `[data-no-drag]`, `[class*="overflow-"]`) and include
  `[role="dialog"]`. Hand-rolled overlays, backdrops, floating toasts and
  clickable cards are the usual victims — their `onClick` never fires, the
  window moves instead. The same regions eat wheel events over scrollable
  content, so scroll containers must be no-drag too. A modal rendered through a
  portal to `document.body` lives outside the drag root and is immune, which is
  a concrete argument for a single modal primitive.
- **An empty handler passed as a prop is a dead click.** `onAlgo={() => {}}`
  renders a button that promises an action and does nothing; it appears when a
  prop is required only so the type checks. Make the prop optional and omit it
  at the call sites.

Sweep both classes statically (a tag-by-tag scan for non-button `onClick`
without a no-drag escape, with brace-depth tracking so `{...}` attributes do not
end the tag early; a line scan for `on[A-Z]\w*={() => {}}`) and keep each scan as
a test, so the next new one fails CI instead of reaching the user.

## Multi-surface UI parity and interactive validation

- Share data selectors, calculation rules and refresh subscriptions across desktop and controller surfaces; sharing the same IPC transport alone does not prevent divergent totals or stale panels. Exercise an update while the panel stays open, discard obsolete responses after selection changes, and preserve the last successful data on transient failures.
- Scope console styling to its shell, including embedded profile, catalog and download interiors; changing only the outer wrapper leaves a visually inconsistent experience, while unscoped rules alter the desktop too.
- Give only the topmost overlay ownership of Back/Escape. Test nested editors, pending saves, scrollable content and restoration to the originating tile; keep that tile mounted in the harness so restoration is actually observable.
- Validate controller polling with press/release edges over multiple frames, including D-pad, confirm, back and analog scrolling. Label simulated Gamepad API results separately from physical-controller and authenticated-backend validation.
- Before handing the user a source-launch command, verify the local Electron executable with `./node_modules/.bin/electron --version` and exercise the launch path where feasible. A successful frontend build does not establish that Electron can start. For binary-install repair, see `references/electron-runtime-install.md`.

## Gates

Run the project's own CI order before claiming done (for a typical Node app: test suite → `tsc --noEmit` → production build). Delete every temporary probe file you created, and say so in the report.

## Reporting a diagnosis

Lead with what the real data says (counts, ids, timestamps from the app's own store and backend), then the mechanism, then the fix. Show a reproduction that fails before the fix and passes after it — a code-reading diagnosis that was never reproduced is a hypothesis, and should be labelled as one.
