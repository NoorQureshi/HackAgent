# Security Policy

SploitAgent is a library of **security skills for authorized testing**. This policy covers two
different things: reporting a vulnerability in SploitAgent's *own* code, and the rules for using it.

## Reporting a vulnerability in SploitAgent itself

If you find a security issue in the tooling in this repo — the `sploit` launcher, `install.sh`, the
`tools/console/` server, the `cc-activity-hook.py`, or `tools/catalog.py` (for example: the console
serving files outside a workspace, a path-traversal, or the installer clobbering files it shouldn't) —
please report it privately, not in a public issue:

1. Go to the repository's **Security** tab → **Report a vulnerability** (GitHub private advisory).
2. Describe the issue, the impact, and steps to reproduce.

We aim to acknowledge within a few days. Please give us a reasonable window to fix it before public
disclosure. There is no bounty, but we credit reporters who want it.

> Maintainers: enable **Settings → Code security → Private vulnerability reporting** so the button
> above appears.

### What is *not* a vulnerability here

The skills describe offensive techniques on purpose — that is the point of the library, not a flaw.
Reports that a `SKILL.md` "teaches hacking" are out of scope. The console binds to `127.0.0.1`, is
read-only, and never controls the agent by design.

## Using SploitAgent — authorized use only

SploitAgent runs real techniques against real systems. Use it **only** where you have explicit
authorization:

- a signed penetration-test scope / statement of work,
- a bug-bounty program whose policy lists the target as in scope, or
- systems you own.

Every engagement loads `tradecraft-scope-roe` first and is bound by the target's `scope.txt`. Do not
point it at anything you are not authorized to test. Using these techniques against systems without
permission is illegal in most jurisdictions. The library is also intended for security education.
The authors are not responsible for misuse.

## No warranty

This project is provided "as is", without warranty of any kind (see [LICENSE](LICENSE)). You are
responsible for how you use it and for staying within the law and your authorization.
