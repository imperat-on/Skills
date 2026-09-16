// Plugin do OpenCode: guards + formatação + auditoria usando os MESMOS scripts
// de hooks/ (fonte única da política). Copie para
//   ~/.config/opencode/plugins/agent-guards.js     (global)
//   .opencode/plugins/agent-guards.js              (por projeto)
// Docs: opencode.ai/docs/plugins
//
// O OpenCode não tem hooks de shell: ele carrega módulos JS. Este arquivo só
// traduz os eventos dele para os scripts Python do kit, então mudar a política
// é editar um arquivo só.
import { spawn } from "node:child_process"

const HOOKS = process.env.SKILLS_KIT_HOOKS || "__HOOKS__"

function invoke(script, payload, cwd) {
  return new Promise((resolve) => {
    const p = spawn(script.endsWith(".py") ? "python3" : "bash", [script], {
      cwd,
      env: { ...process.env, SKILLS_KIT_STYLE: "hermes" },
    })
    let err = ""
    p.stdout.on("data", () => {})
    p.stderr.on("data", (d) => { err += d.toString() })
    p.on("close", (code) => resolve({ code, stderr: err.trim() }))
    p.on("error", () => resolve({ code: 0, stderr: "" })) // falha aberta: nunca trava o agente
    p.stdin.end(JSON.stringify(payload))
  })
}

const FILE_TOOLS = new Set(["write", "edit", "multiedit", "patch", "notebookedit"])

export const AgentGuards = async ({ directory, worktree }) => {
  const cwd = worktree || directory || process.cwd()

  return {
    "tool.execute.before": async (input, output) => {
      const tool = String(input.tool || "").toLowerCase()
      const args = output.args || {}
      const payload = {
        hook_event_name: "PreToolUse",
        tool_name: tool,
        tool_input: {
          command: args.command ?? "",
          file_path: args.filePath ?? args.file_path ?? args.path ?? "",
          content: args.content ?? args.newString ?? args.new_string ?? "",
        },
        cwd,
      }

      if (tool === "bash" || tool === "shell") {
        const r = await invoke(`${HOOKS}/guard-dangerous.py`, payload, cwd)
        if (r.code === 2) throw new Error(r.stderr || "bloqueado por política local")
      }
      if (FILE_TOOLS.has(tool) || tool === "read") {
        const r = await invoke(`${HOOKS}/guard-secrets.py`, payload, cwd)
        if (r.code === 2) throw new Error(r.stderr || "bloqueado por política local")
      }
    },

    "tool.execute.after": async (input, output) => {
      const tool = String(input.tool || "").toLowerCase()
      const args = output.args || {}
      const filePath = args.filePath ?? args.file_path ?? args.path ?? ""
      if (FILE_TOOLS.has(tool) && filePath) {
        await invoke(`${HOOKS}/auto-format.sh`, { hook_event_name: "PostToolUse", tool_name: tool, tool_input: { file_path: filePath }, cwd }, cwd)
      }
      await invoke(`${HOOKS}/audit-log.sh`, { hook_event_name: "PostToolUse", tool_name: tool, tool_input: args, cwd }, cwd)
    },

    event: async ({ event }) => {
      if (event?.type === "session.idle") {
        await invoke(`${HOOKS}/notify-stop.sh`, { hook_event_name: "Stop", cwd, message: "sessão ociosa" }, cwd)
      }
    },
  }
}
