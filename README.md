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

## Clipper: automatische Viral-Clips von Top-Streamern

Pipeline: Top-Streamer einer Kategorie (z.B. GTA 6) -> Chat-Spikes erkennen -> Twitch-Clip erstellen -> als 9:16 rendern (Blur-Hintergrund, Streamer-Credit, optional Untertitel) -> `out/` mit fertigem Video + Caption-Vorschlag. Gepostet wird von dir.

Setup:
1. App auf https://dev.twitch.tv/console anlegen (Client-Typ "Public" für Device-Login reicht nicht für App-Token: "Confidential" wählen), dann
   `export TWITCH_CLIENT_ID=... TWITCH_CLIENT_SECRET=...`
2. `pip install -r requirements.txt` (ffmpeg muss installiert sein)
3. `python -m clipper auth` (einmaliger Login im Browser, Scope `clips:edit`)
4. `python -m clipper run` – läuft dauerhaft; `clipper/config.yaml` steuert Spiel, Sprachen, Spike-Empfindlichkeit, Clip-Limit.

Nur rendern: `python -m clipper render in.mp4 out.mp4`.

Hinweis: Clips fremder Streamer gehören den Streamern. Immer Credit nennen (wird eingeblendet) und bei Monetarisierung vorher um Erlaubnis fragen.
