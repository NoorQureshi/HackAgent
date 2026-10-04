# SploitAgent — for Claude Code

You are in **SploitAgent**, an open library of security skills. Use it via the operating guide below,
which applies to every agent:

@AGENTS.md

## Claude Code specifics
- The files under `skills/` are in the standard **Agent Skills** format, organised by domain
  (`skills/<domain>/<slug>/SKILL.md`). Run `./install.sh` once to wire them into every detected
  agent — it links each skill into `~/.claude/skills/` (the one-directory-deep layout Claude Code
  expects) and configures Kimi Code, Cursor, Codex, and Gemini the same way or via a managed
  pointer block (use `--project` for just this repo, `--uninstall` to remove). Opening Claude Code
  inside this repo also works without installing, via this file.
- When a task matches a skill's trigger, load that `skills/<domain>/<slug>/SKILL.md` and follow it.
- **Always load `tradecraft-scope-roe` first** and confirm authorization before acting.
