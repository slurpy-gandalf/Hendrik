# Hendrik

## Claude Code setup: REA (Reverse Engineer Anything)

This repo ships the [REA](https://github.com/morluto/rea) skill and MCP server for Claude Code:

- `.claude/skills/reverse-engineer-anything/`: the `reverse-engineer-anything` skill, copied from morluto/rea @ `6a0ccf7` (MIT).
- `.mcp.json`: registers the `rea` MCP server (`npx -y rea-agents@6.8.0 mcp`), pinned to the same release as the skill.

On first use, Claude Code asks you to approve the project MCP server `rea`.

Requirements: Node.js 22.x (>=22.23.4), 24.x (>=24.22.1) or 26.12.1+, and a procps `ps` on Linux.
Native-binary decompilation also needs Hopper, Ghidra, IDA or Kuna. Static analysis of JavaScript/Electron
apps, archives, Go binaries, model files and similar targets needs no extra engine.

To update: bump the version in `.mcp.json`, then re-copy `.agents/skills/reverse-engineer-anything` from the matching REA release.
