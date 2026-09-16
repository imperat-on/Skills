#!/usr/bin/env bash
# Adiciona os MCPs no Prime Agent (ele guarda tudo em ~/.prime/agent/settings.json).
#   ./mcp-add.sh            # roda de verdade
#   ./mcp-add.sh --dry-run  # só mostra
set -u
DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

echo "+ context7"
if [ "$DRY" = "1" ]; then echo "  prime-agent mcp add context7 --env CONTEXT7_API_KEY=<opcional, aumenta rate limit> -- npx -y @upstash/context7-mcp@4.1.1"; else prime-agent mcp add context7 --env CONTEXT7_API_KEY=<opcional, aumenta rate limit> -- npx -y @upstash/context7-mcp@4.1.1; fi
echo "+ filesystem"
if [ "$DRY" = "1" ]; then echo "  prime-agent mcp add filesystem -- npx -y @modelcontextprotocol/server-filesystem@2026.8.31 ~/Documents/projects"; else prime-agent mcp add filesystem -- npx -y @modelcontextprotocol/server-filesystem@2026.8.31 ~/Documents/projects; fi
echo "+ memory"
if [ "$DRY" = "1" ]; then echo "  prime-agent mcp add memory --env MEMORY_FILE_PATH=~/.local/state/mcp-memory/memory.json -- npx -y @modelcontextprotocol/server-memory@2026.8.31"; else prime-agent mcp add memory --env MEMORY_FILE_PATH=~/.local/state/mcp-memory/memory.json -- npx -y @modelcontextprotocol/server-memory@2026.8.31; fi
echo "+ sequential-thinking"
if [ "$DRY" = "1" ]; then echo "  prime-agent mcp add sequential-thinking -- npx -y @modelcontextprotocol/server-sequential-thinking@2026.8.31"; else prime-agent mcp add sequential-thinking -- npx -y @modelcontextprotocol/server-sequential-thinking@2026.8.31; fi
echo "+ git"
if [ "$DRY" = "1" ]; then echo "  prime-agent mcp add git -- uvx mcp-server-git --repository ."; else prime-agent mcp add git -- uvx mcp-server-git --repository .; fi
echo "+ fetch"
if [ "$DRY" = "1" ]; then echo "  prime-agent mcp add fetch -- uvx mcp-server-fetch"; else prime-agent mcp add fetch -- uvx mcp-server-fetch; fi
echo "+ time"
if [ "$DRY" = "1" ]; then echo "  prime-agent mcp add time -- uvx mcp-server-time --local-timezone=America/Sao_Paulo"; else prime-agent mcp add time -- uvx mcp-server-time --local-timezone=America/Sao_Paulo; fi
echo "+ playwright"
if [ "$DRY" = "1" ]; then echo "  prime-agent mcp add playwright -- npx -y @playwright/mcp@0.0.81"; else prime-agent mcp add playwright -- npx -y @playwright/mcp@0.0.81; fi
echo "+ chrome-devtools"
if [ "$DRY" = "1" ]; then echo "  prime-agent mcp add chrome-devtools -- npx -y chrome-devtools-mcp@1.9.0"; else prime-agent mcp add chrome-devtools -- npx -y chrome-devtools-mcp@1.9.0; fi
echo "+ github"
if [ "$DRY" = "1" ]; then echo "  prime-agent mcp add github --url https://api.githubcopilot.com/mcp/"; else prime-agent mcp add github --url https://api.githubcopilot.com/mcp/; fi
echo "+ sentry"
if [ "$DRY" = "1" ]; then echo "  prime-agent mcp add sentry --env SENTRY_HOST=sentry.io --env SENTRY_ACCESS_TOKEN=<token> -- npx -y @sentry/mcp-server@0.39.0"; else prime-agent mcp add sentry --env SENTRY_HOST=sentry.io --env SENTRY_ACCESS_TOKEN=<token> -- npx -y @sentry/mcp-server@0.39.0; fi
echo "+ everything"
if [ "$DRY" = "1" ]; then echo "  prime-agent mcp add everything -- npx -y @modelcontextprotocol/server-everything@2026.8.31"; else prime-agent mcp add everything -- npx -y @modelcontextprotocol/server-everything@2026.8.31; fi
echo "+ figma"
if [ "$DRY" = "1" ]; then echo "  prime-agent mcp add figma --env FIGMA_API_KEY=<token read-only do Figma> -- npx -y figma-developer-mcp@0.13.2 --stdio"; else prime-agent mcp add figma --env FIGMA_API_KEY=<token read-only do Figma> -- npx -y figma-developer-mcp@0.13.2 --stdio; fi

echo
echo "confira com: prime-agent mcp list"
