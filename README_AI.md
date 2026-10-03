# SploitAgent — bootstrap for AI agents

You are an AI agent. This repo is a **skill library**: 161 trigger-loaded security skills across 20
domains, offensive and defensive. The full operating guide is [AGENTS.md](AGENTS.md) — read it when
you can; this file is the short version.

## Rule zero — authorization before anything
Before you touch any target, load `skills/tradecraft/tradecraft-scope-roe/SKILL.md` and confirm one
of: a signed pentest scope, a bug-bounty program listing the target in scope, or systems the user
owns. **If scope is unclear, stop and ask the user.** Never scan, request, or exploit anything
outside the confirmed envelope.

## How to load a skill
Match the task in front of you to a skill's `description:` trigger line — skim
[CATALOG.md](CATALOG.md) (the full index) or grep `skills/`. The routing overview is
[skills/README.md](skills/README.md). Then load that one `skills/<domain>/<slug>/SKILL.md` and work
its sections in order: **When it applies · Why it works · Method (exact commands) · Gotchas ·
Verify success.**

## The loop
1. Confirm scope, write `scope.txt`; plan with `tradecraft-attack-scenarios`.
2. Recon — `recon-*`.
3. Attack surface — identify what you're looking at, then work that surface's checklist
   (`web-testing-checklist`, `api-testing-checklist`, `code-review-methodology`) top-to-bottom as
   your coverage map; it routes you into the domain's deep skills.
4. Foothold — drive a weakness to proven impact; chain small bugs with `exploit-chaining`.
5. Escalate & pivot — `privesc-*`, `ad-*`, `network-pivoting-tunneling`; pick the next lead with
   `tradecraft-pivot-decisions`.
6. Report — validate with `reporting-triage-validation`, then `reporting-bug-bounty-writeup` or
   `reporting-pentest-report`. Defensive tasks: `defense-*`.

## Working rules
- **Work one lead at a time**; load the next skill as new leads appear.
- **Prove impact** with the least data and action needed. One failed payload is not "not
  vulnerable" — work the variation matrix (every injection point, context, encoding, blind variant)
  before you rule a class out, and record what you actually tried.
- **Write findings** as you confirm them: `findings/<nn>-<slug>.md` with summary, numbered
  reproduction steps, proof, impact, and remediation — so a human can reproduce every claim.
- Keep `plan.md` and `notes.md` current, and log decisions/findings (lead, status, rationale) to
  `.sploit/activity.jsonl` so a human can follow and audit you.
- Minimize footprint; clean up test artifacts (accounts, uploads) when done.

If this repo was cloned into your workspace, everything you need is local — there is nothing to
install or configure before you start.
