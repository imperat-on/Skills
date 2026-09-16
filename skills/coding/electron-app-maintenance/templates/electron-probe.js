// TEMPORARY PROBE — copy into the APP DIRECTORY as .probe.<name>.js, run with
// `npx electron .probe.<name>.js`, then DELETE IT.
//
// Why inside the app dir: the app name drives the OS-keyring entry used to
// encrypt the stored session, so a probe run from elsewhere may fail to decrypt.
// Prints counts/ids only — never a token or a user payload.
const path = require("node:path")
const { app } = require("electron")

async function main() {
  // point these at the app's real modules
  const { getClient, restoreSession } = require(path.join(__dirname, "electron/<client-module>"))
  const { loadSession } = require(path.join(__dirname, "electron/<session-module>"))

  const saved = loadSession()
  console.log("session on disk:", saved ? "ok (decrypted)" : "missing/failed")
  if (!saved) return app.exit(0)

  await restoreSession()
  const client = getClient()
  const { data: user } = await client.auth.getUser()
  console.log(
    "authenticated:",
    Boolean(user?.user?.id),
    "| user:",
    user?.user?.user_metadata?.username || "-",
  )

  const { data, error } = await client.rpc("<rpc-name>", { <args> })
  if (error) {
    console.log("RPC error:", error.message || error)
    return app.exit(0)
  }
  const rows = Array.isArray(data) ? data : []
  console.log("rows:", rows.length)

  // Aggregate in code; print the smallest thing that answers the question.
  const por = new Map()
  for (const r of rows) por.set(String(r.key), (por.get(String(r.key)) || 0) + 1)
  console.log(
    "by key:",
    JSON.stringify([...por.entries()].sort((a, b) => b[1] - a[1]).slice(0, 25)),
  )
}

app.whenReady().then(() =>
  main()
    .catch((e) => console.log("EXC:", e?.message || e))
    .finally(() => setTimeout(() => app.exit(0), 300)),
)
