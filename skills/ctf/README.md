# CTF playbooks — `ctf` skills

Capture-the-flag playbooks: challenge triage and time budgeting, plus per-category speed-run
guides (web, pwn, crypto, rev, forensics) that route into the deep technique skills in the
other domains.

Add a skill here:
```bash
cp -r skills/_templates/technique.md skills/ctf/<slug>/SKILL.md
# edit frontmatter (domain: ctf) + body, then:
python3 tools/catalog.py
```

Naming: domain-prefixed kebab-case, e.g. `ctf-<thing>`. See the full table in [`CATALOG.md`](../../CATALOG.md).
