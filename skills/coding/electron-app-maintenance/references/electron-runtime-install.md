# Repairing a local Electron runtime installation

Use when the JavaScript package resolves but the CLI reports an incomplete Electron installation.

1. Read the installed `node_modules/electron/package.json`, `index.js` and `install.js`. Check the executable and `path.txt` expected by that installed version; do not replace or upgrade the dependency blindly.
2. Run `node node_modules/electron/install.js` from the application directory. If the installer explicitly skips downloads because `ELECTRON_SKIP_BINARY_DOWNLOAD` is set, unset it for this invocation only. Verify the executable afterwards rather than trusting a zero exit code.
3. If the installer still produces no runtime, download the official archive for the exact installed version, host platform and architecture from the Electron GitHub release. Verify SHA-256 against the matching entry in the installed package's `checksums.json` before extraction; stop if it differs.
4. Extract the verified archive into `node_modules/electron/dist` with a real archive extractor. Create `node_modules/electron/path.txt` containing the platform-relative executable expected by `index.js` (Linux: `electron`, with no extra newline). Preserve archive executable permissions. Keep these dependency repairs out of Git and leave application data untouched.
5. Run `./node_modules/.bin/electron --version`; then use the repository's actual launch script. Report runtime-version verification separately from an observed application window: the former proves the binary runs, not that authenticated IPC or the UI is healthy.

Do not repeat an installer merely because it exits successfully: missing output files mean the repair has not landed. Use the verified archive fallback only after inspecting the installed package's layout.
