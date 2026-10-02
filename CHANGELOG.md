# Changelog

All notable changes to SploitAgent are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **`bench/` benchmark harness** — proves with numbers that an agent + SploitAgent
  skills outperforms the same agent without them. Runs Claude Code headless against
  a local OWASP Juice Shop target in two arms (skills vs baseline), scores from the
  target's own solve log, and publishes `bench/RESULTS.md`. `python3 bench/run.py
  setup|run|report`; see `bench/README.md`.
- **Attack Map** in the `sploit watch` console — reconstructs an engagement as a
  scope → surface → leads decision graph (status, reasoning, steps, linked findings).
- **Notes** tab in the console; the finding drawer renders full Markdown (code, tables).
- **Claude Code auto-capture hook** (`tools/hooks/cc-activity-hook.py`) — records shell
  commands and web requests into the workspace activity log automatically.
- Community health files: `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue/PR templates.
- `tools/check.sh` — run the same checks as CI locally.
- `sploit version`.

### Changed
- Console redesign: cleaner layout, live diff-based updates, severity summary.
- README and docs rewritten in plainer language with a glossary and real screenshots.

### Fixed
- `sploit` / `install.sh` resolve their real location through a PATH symlink
  (previously `sploit new`/`sploit watch` broke when run via `~/.local/bin/sploit`).
- `sploit watch` verifies the console actually started instead of reporting false success.
- Severity parsed from `**Severity:**` / `## Severity` in finding files.

### CI
- Drift check now also guards `docs/skills.json`.
- All Python files compile-checked; shell scripts linted with `shellcheck`.
- Least-privilege `permissions:` and `concurrency` added to the workflow.

<!--
When cutting a release, move the items above under a version heading, e.g.:

## [1.0.0] - 2026-09-10
-->
