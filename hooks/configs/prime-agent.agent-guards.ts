// Extensão do Prime Agent: guards + formatação + auditoria reusando os scripts
// de hooks/. Copie para ~/.prime/agent/extensions/agent-guards.ts (global) ou
// .prime/agent/extensions/ (por projeto) e rode /reload.
// Docs: <pacote prime-agent>/docs/extensions.md (evento `tool_call` pode bloquear)
import { spawn } from "node:child_process"
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent"

const HOOKS = process.env.SKILLS_KIT_HOOKS || "__HOOKS__"
const FILE_TOOLS = new Set(["write", "edit", "patch"])

function invoke(script: string, payload: unknown, cwd: string) {
  return new Promise<{ code: number; stderr: string }>((resolve) => {
    const p = spawn(script.endsWith(".py") ? "python3" : "bash", [script], {
      cwd,
      env: { ...process.env, SKILLS_KIT_STYLE: "hermes" },
    })
    let err = ""
    p.stderr.on("data", (d) => (err += d.toString()))
    p.on("close", (code) => resolve({ code: code ?? 0, stderr: err.trim() }))
    p.on("error", () => resolve({ code: 0, stderr: "" })) // falha aberta
    p.stdin.end(JSON.stringify(payload))
  })
}

export default function (pi: ExtensionAPI) {
  let cwd = process.cwd()

  pi.on("session_start", async (_event, ctx: any) => {
    cwd = ctx?.cwd || ctx?.sessionManager?.getCwd?.() || cwd
  })

  pi.on("tool_call", async (event: any) => {
    const tool = String(event.toolName || "").toLowerCase()
    const input = event.input || {}
    const payload = {
      hook_event_name: "PreToolUse",
      tool_name: tool,
      tool_input: {
        command: input.command ?? "",
        file_path: input.filePath ?? input.path ?? "",
        content: input.content ?? input.newString ?? input.new_string ?? "",
      },
      cwd,
    }

    if (tool === "bash" || tool === "shell") {
      const r = await invoke(`${HOOKS}/guard-dangerous.py`, payload, cwd)
      if (r.code === 2) return { block: true, reason: r.stderr || "bloqueado por política local" }
    }
    if (FILE_TOOLS.has(tool) || tool === "read") {
      const r = await invoke(`${HOOKS}/guard-secrets.py`, payload, cwd)
      if (r.code === 2) return { block: true, reason: r.stderr || "bloqueado por política local" }
    }
  })

  pi.on("tool_result", async (event: any) => {
    const tool = String(event.toolName || "").toLowerCase()
    const input = event.input || {}
    const filePath = input.filePath ?? input.path ?? ""
    if (FILE_TOOLS.has(tool) && filePath) {
      await invoke(`${HOOKS}/auto-format.sh`, { hook_event_name: "PostToolUse", tool_name: tool, tool_input: { file_path: filePath }, cwd }, cwd)
    }
    await invoke(`${HOOKS}/audit-log.sh`, { hook_event_name: "PostToolUse", tool_name: tool, tool_input: input, cwd }, cwd)
  })
}
