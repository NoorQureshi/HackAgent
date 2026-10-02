# Using SploitAgent

SploitAgent is a **library of security skills** in the standard Agent-Skills format
(`skills/<domain>/<slug>/SKILL.md`, each with a `description:` trigger line). You give an AI agent
access to the skills; it loads the right one for the task. There's **no runtime to install** — the
skills are plain Markdown.

Two building blocks matter:
- **`AGENTS.md`** — the operating guide (scope-first, the loop, how to pick a skill, per-engagement structure).
- **`skills/`** — the 161 skills themselves; **`CATALOG.md`** is the browsable index.

Below are copy-paste setups and **example prompts** for each agent, plus local LLMs.

---

## Claude Code

**Option A — open Claude Code in the repo (zero setup).** It auto-reads `CLAUDE.md` (which imports
`AGENTS.md`) and can load any `skills/**/SKILL.md`.
```bash
git clone https://github.com/NoorQureshi/SploitAgent && cd SploitAgent
claude
```
Then, e.g.:
> *"My authorized target is the bug-bounty program acme.com (wildcard in scope). Load SploitAgent's recon skills and map the surface, then hunt the API."*

**Option B — make the skills available in every project.** Run the installer once; it links each
skill into `~/.claude/skills/` in the one-directory-deep layout Claude Code expects (a plain
`ln -s` of the whole `skills/` tree won't work, because the skills are nested under domain folders):
```bash
git clone https://github.com/NoorQureshi/SploitAgent
cd SploitAgent && ./install.sh          # --project scopes to one repo · --uninstall removes
```
Now in any project: `"Use the web-ssrf skill on https://app.example.com (authorized)."`

---

## Codex CLI (OpenAI)

Codex reads **`AGENTS.md`** from the working directory automatically.
```bash
git clone https://github.com/NoorQureshi/SploitAgent && cd SploitAgent
codex           # it picks up AGENTS.md; point it at skills/ as needed
```
> *"Read AGENTS.md, then use skills/api/api-bola to test https://api.example.com/v1 (I'm authorized)."*

For a one-off without cloning, paste a single `SKILL.md` into the chat and give your target.

---

## Gemini CLI

Gemini CLI reads context files from the working directory (`GEMINI.md`/`AGENTS.md` conventions).
Point it at the guide + a skill:
```bash
git clone https://github.com/NoorQureshi/SploitAgent && cd SploitAgent
gemini
```
> *"Follow AGENTS.md. Load skills/web/web-xss and test the search box at https://example.com (authorized)."*

If your version doesn't auto-read `AGENTS.md`, start the session by pasting it (`cat AGENTS.md`).

---

## Cursor / Windsurf / Zed (and other AGENTS.md-aware editors)

These read `AGENTS.md` (or their rules file) from the repo root. Clone SploitAgent (or add it to your
workspace) and reference skills by path:
> *"Per AGENTS.md, use `skills/cloud/cloud-imds-ssrf` — I have an SSRF on an AWS-hosted authorized target."*

To use the skills inside *another* project, add SploitAgent as a folder in the workspace, or copy the
domains you want into that repo.

---

## aider (works great with local or hosted models)

`aider` can load files as read-only context with `--read`:
```bash
git clone https://github.com/NoorQureshi/SploitAgent && cd SploitAgent
aider --read AGENTS.md --read skills/web/web-ssrf/SKILL.md          # hosted model
aider --model ollama/qwen2.5-coder:14b --read AGENTS.md             # local model
```
Then describe the authorized target and the task.

---

## Local LLMs

Local models don't auto-discover files, so you feed the guide + the relevant skill into context.

### Ollama — bake the guide into a model (best experience)
Create a local model preloaded with the operating guide:
```bash
git clone https://github.com/NoorQureshi/SploitAgent && cd SploitAgent
printf 'FROM qwen2.5-coder:14b\nSYSTEM """\n%s\n"""\n' "$(cat AGENTS.md)" > Modelfile
ollama create sploitagent -f Modelfile
ollama run sploitagent
```
Then paste the specific skill for the task and your target:
```bash
# feed a skill + your task in one shot
cat skills/web/web-ssrf/SKILL.md - <<<'Target https://app.example.com (authorized). Walk me through SSRF testing.' | ollama run sploitagent
```

### LM Studio
- Set the **System Prompt** to the contents of `AGENTS.md`.
- Attach (or paste) the `SKILL.md` files for the domains you're working, then give your target.

### Open WebUI
- Create a **Knowledge** collection and upload the `skills/` folder (or the domains you need).
- In chat, reference it with `#` so the model retrieves the relevant skill, e.g. `#sploitagent web-ssrf`.

### Any local setup (lowest common denominator)
The skills are just text — concatenate the guide + skill + your task into the prompt:
```bash
{ cat AGENTS.md; cat skills/api/api-graphql/SKILL.md; echo "Target: https://api.example.com/graphql (authorized). Plan the test."; } > prompt.txt
# paste prompt.txt into any local chat UI
```

---

## Any other / open-source agent

There's no lock-in. Give the agent read access to `skills/` (and `AGENTS.md`), or load the specific
`SKILL.md` for the task. If the framework supports a knowledge/RAG store, index `skills/` and let it
retrieve by the task description — the `description:` lines are written to match on real signals.

---

## Example prompts that work well

- *"Authorized pentest, scope in scope.txt. Start with recon-subdomain-enum, then route web hosts to the web-* skills."*
- *"I have valid domain creds on an internal AD pentest. Use ad-kerberoasting, then check ADCS with ad-adcs."*
- *"Testing an LLM chatbot (authorized). Use ai-prompt-injection and ai-mcp-security to assess it."*
- *"Blue team: turn the ssrf finding into a detection with defense-detection-sigma."*
- *"Found a bug — write it up with reporting-bug-bounty-writeup at the right CVSS severity."*

## The rule that comes first

Every engagement starts with **scope**. The agent should load `tradecraft-scope-roe` and confirm
you're inside a signed pentest scope, a bug-bounty program you're in scope for, or systems you own.
Never point these skills at anything else. Full method: [`../methodology.md`](../methodology.md).
