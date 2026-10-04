# SploitAgent — operating guide for AI agents

You are an AI agent (Claude Code, Codex, Gemini, or any other) working with SploitAgent, a library of
security skills. This file tells you how to use it. Keep it short in your head: **confirm scope →
pick the skill that matches the task → follow it → prove impact → report.**

## What you have here
- `skills/<domain>/<slug>/SKILL.md` — 206 trigger-loaded skills across 20 domains (offensive **and**
  defensive). Each has a `description:` that says *when* to load it, and a body that teaches the mechanism.
- `CATALOG.md` — the full, browsable index of every skill.
- `COVERAGE.md` — how skills map to OWASP / MITRE ATT&CK / CWE.
- `methodology.md` — the full engagement method (this file is the short version).

## Rule zero — scope, always first
Never scan, request, or exploit anything outside a **confirmed authorization envelope**. Before you
touch a target, load `skills/tradecraft/tradecraft-scope-roe/SKILL.md` and confirm one of:
a signed pentest scope, a bug-bounty program the target is in scope for, or systems the user owns.
**If scope is unclear, STOP and ask the user.** Never touch out-of-scope or third-party systems.

## How to pick a skill
Match the task in front of you to a skill's `description:` trigger line (skim `CATALOG.md`, or
grep `skills/`). Load that one `SKILL.md` and work its sections in order:
**When it applies · Why it works · Method (exact commands) · Gotchas · Verify success.**
Work one lead at a time; load the next skill as new leads appear.

## The loop (how to work a target)
1. **Set up & plan** — create the engagement workspace (below), or run `./sploit new <target>` to
   scaffold it; write `scope.txt` (+ `roe.md` for bug bounty). Then load `tradecraft-attack-scenarios`
   to turn the objective + scope into an ordered plan, and re-plan as evidence comes in.
2. **Recon** — `recon-*` (subdomains, DNS, content/JS discovery, OSINT, services).
3. **Attack surface** — first identify *what you're looking at*, then **load that surface's
   methodology/checklist and work it top-to-bottom** as your coverage map (don't pivot off it until
   each phase is genuinely done): web app → `web-testing-checklist`, API → `api-testing-checklist`,
   source → `code-review-methodology`. Each phase routes into the domain's deep technique skills:
   web → `web-*`, APIs → `api-*`, cloud → `cloud-*`, mobile → `mobile-*`, Active Directory → `ad-*`,
   perimeter/appliances → `network-*`, Wi-Fi → `wireless-*`, LLM/AI targets → `ai-ml/*`,
   binaries/firmware → `reverse-engineering-*`, weak crypto / encrypted tokens → `cryptography-*`.
   (No surface checklist yet for host/cloud/mobile/AD/LLM — route by domain and cover systematically.)
4. **Foothold** — drive a weakness to proven impact; combine small bugs with `exploit-chaining`.
5. **Escalate & pivot** — after every result, use `tradecraft-pivot-decisions` to choose the next
   lead; `privesc-*`, `ad-*`, `network-pivoting-tunneling`; map multi-step routes with
   `tradecraft-attack-path-mapping`.
6. **Report** — validate first with `reporting-triage-validation`, then `reporting-bug-bounty-writeup`
   or `reporting-pentest-report`.
7. **Defend** (if asked) — `defense-*` (detection, hardening, DFIR, threat modeling).

**Human-factor work** (`social-eng-*`) is a separate, **pentest-only** track with stricter
authorization — load `social-eng-methodology` first and never run it on a bug-bounty target.

## Per-engagement structure (create this, keep it tidy)
For each target, work inside its own folder so notes and loot never mix or leak:

```
engagements/<target>/
  scope.txt              # authorized targets — the hard boundary
  roe.md                 # bug-bounty rules of engagement (rate limits, don'ts, disclosure)
  plan.md                # your living strategy — what you'll test, in what order, why
  notes.md               # timestamped running log — the source of truth for the report
  findings/              # confirmed findings + evidence, one file per finding
  loot/                  # captured data / artifacts
  .sploit/activity.jsonl # one JSON line per step, so a human/console can follow you
```

## Show your work — so a human can follow *and* audit you
Externalise your reasoning into the workspace as you go, so anyone — a teammate, or the read-only
`sploit watch` console — can see not just *what* you did but *why*, across **any** tool (Claude Code,
OpenCode, Codex, Gemini, an API script). Three files carry it:

### 1. `plan.md` — the living strategy
Write it up front and keep it current: the objective, an ordered strategy as a checkbox list (tick
items as you go), and a one-line "current focus". This is your thinking, on disk.

### 2. `.sploit/activity.jsonl` — one JSON line per meaningful step
This is the spine of the console's **Attack Map** and timeline. Append a line whenever you decide
something, try something, or learn something:

```
{"ts":"<ISO-8601 UTC>","event":"<type>","detail":"…","lead":"<slug>","surface":"<name>",
 "status":"<status>","rationale":"why","skill":"<slug>","severity":"<sev>","refs":"<finding-file>"}
```

- **Required:** `ts`, `event`, `detail`.
- **`event`** — one of `plan · decision · skill_load · command · result · finding · note`.
- **`lead`** — *the most important optional field.* A short slug for the attack lead this step
  belongs to (`command-injection`, `lfi`, `jwt-none-alg`, `s3-public-bucket`). Steps that share a
  `lead` are grouped into one branch of the Attack Map. Pick the slug when you open a lead and reuse
  it for every step on it.
- **`surface`** — the higher grouping the lead sits under (`DVWA web app`, `REST API`, `AD domain`).
- **`status`** — for `decision`/`finding` steps, where the lead stands: `open` (identified, not
  started) · `trying` · `confirmed` · `failed` (ruled out **after working the variation matrix** —
  see House rules; one failed payload is `open`, not `failed`) · `blocked` (can't proceed —
  say why in `rationale`) · `skipped` / `not-attempted` (say why). This is how the map shows what you
  **proved, ruled out, and deliberately left** — including anything you couldn't get to.
- **`rationale`** — *why* you made this decision or what a result means. This is the reasoning a
  manual investigator needs. Always set it on `decision` steps.
- **`skill`** on `skill_load`; **`severity`** (`critical|high|medium|low|info`) + **`refs`** (the
  `findings/*.md` filename) on `finding`.

**Log the reasoning layer religiously:** a `decision` with `lead` + `rationale` + `status` every time
you open, rule out, or park a lead; a `finding` with `severity` + `refs` when you confirm one. If you
are running under **Claude Code**, the auto-capture hook (`.sploit/cc-activity-hook.py`, wired in
`.claude/settings.json`) already records your shell commands and web requests, so you don't need to
log routine `command`/`result` lines by hand — spend your logging on decisions, leads, and findings.
Under any other tool, also log the key `command`/`result` steps yourself.

### 3. `notes.md` + `findings/*.md` — written for a human to read
Keep `notes.md` as a running log to the teach-the-mechanism standard in `methodology.md`
(**goal · command · result · why it worked · next lead**) — one dated block per lead. Write each
confirmed issue as its own `findings/<nn>-<slug>.md` in this structure (the console renders it, and
it drops straight into a report):

```
# <Vuln class> on <asset> — <one-line impact>

**Severity:** <Critical|High|Medium|Low|Info>
**Endpoint:** `<method + path / component>`

## Summary            <!-- what, where, why it matters, in 2–3 sentences -->
## Steps to reproduce <!-- numbered, copy-pasteable, exact requests -->
## Proof              <!-- minimal evidence that proves impact -->
## Impact             <!-- realistic business consequence, tied to what you proved -->
## Remediation        <!-- the correct fix -->
```

These paths are git-ignored, so an engagement run inside a clone never pollutes the repo.

## House rules
- **Be thorough — don't quit a lead after one payload.** A single failed test does *not* mean
  "not vulnerable". Before you mark a class clean (`status:"failed"`), work the **variation matrix**:
  - every **injection point** (each param, plus headers, cookies, JSON fields, path segments),
  - every **context** (e.g. XSS: HTML body / attribute / JS string / URL / event handler; SQLi:
    numeric vs string vs order-by vs second-order),
  - **encodings & filter bypasses** (URL/double/unicode/case, comment-splitting, the skill's WAF list),
  - **blind / out-of-band** variants when there's no visible response (time, boolean, OOB callback).
  Use the skill's `cheatsheet.md` (where present) as the checklist — try the set, not the first line.
  `failed` means *ruled out after covering these*; record in `rationale` **what you actually tried**
  so a human can trust the "clean". If you only ran a couple of tests, the honest status is `open`,
  not `failed`. (Under Claude Code this is **enforced**: a Stop hook won't let you end the turn while
  a lead is marked `failed` with no coverage rationale — it sends you back to go deeper.)
- Teach the mechanism, don't just paste payloads. Prove impact with the least data/action needed.
- Minimize footprint; clean up test artifacts (accounts, uploads).
- Authorized use only — this library is for pentest engagements, bug-bounty programs, and defense.
