# Skills library

The heart of SploitAgent: trigger-tagged skills an AI agent auto-loads for the task at hand. Each skill
is `skills/<domain>/<slug>/SKILL.md` with schema-validated frontmatter; its `description:` line is
written so it loads on the right signals (service, vuln class, error string, port).

**Browse the full table in [`../CATALOG.md`](../CATALOG.md)** (generated). This file is the map.

## Organized by domain × type × stability × modes
- **Domain** (the folder): `recon web api mobile cloud network wireless ad ai-ml code-review
  exploit-dev reverse-engineering cryptography privesc defense payloads reporting automation
  tradecraft social-eng`.
- **Type** (`type:`): `arsenal` (tool selection) · `technique` (a concrete chain) · `methodology`
  (how to operate) · `checklist` · `reference` (payloads/tables).
- **Stability** (`stability:`): 🔒 `locked` (curated core — change deliberately) · ✍️ `learning`
  (the open contribution surface — new techniques land here).
- **Modes** (`modes:`): the authorization context a skill is valid in — `pentest`, `bugbounty`,
  `defense`. The `tradecraft-scope-roe` skill governs these.

## Mappings power the coverage view
Skills carry optional `owasp` / `owasp_llm` / `owasp_api` / `mitre` / `cwe` / `severity` fields.
`python3 tools/catalog.py` rolls them into `data/skills_index.json` so coverage can be measured.

## Add a skill (most welcome contribution)
```bash
cp skills/_templates/technique.md skills/<domain>/<slug>/SKILL.md
# fill in frontmatter (strong trigger signals!) + body, then:
python3 tools/catalog.py validate   # schema check
python3 tools/catalog.py            # regenerate CATALOG.md + index
```
House voice: terse, teach-the-mechanism — *when it applies · why it works · method (exact commands
+ flag gloss) · gotchas · verify success*. Authorized use only; no real targets/creds/secrets. See
each domain's `README.md` for what belongs there, and the repo `CONTRIBUTING.md` for the checklist.
