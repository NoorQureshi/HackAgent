# Roadmap & help wanted

SploitAgent grows through contributions. This is the running list of skills we'd love to add — pick
one, write it (see [CONTRIBUTING.md](CONTRIBUTING.md)), open a PR. Struck-through items are done.

**New to contributing?** Anything tagged 🟢 is a great first skill — a well-understood, single
technique with plenty of public references.

## Web
- ✅ ~~`web-host-header` — host-header injection (password-reset poisoning, routing, cache)~~
- ✅ ~~`web-clickjacking` — framing/UI-redress, and when it's actually impactful~~
- 🟢 `web-open-graph-ssrf` — link-preview/oEmbed SSRF variants
- ✅ ~~`web-websocket` — WebSocket hijacking, message tampering, CSWSH~~
- ✅ ~~`web-rate-limit-bypass` — the many ways rate limits fail (headers, casing, parallelism)~~
- ✅ ~~`web-dependency-confusion` — internal package name takeover~~
- ✅ ~~`web-saml` — SAML assertion/signature-wrapping attacks~~
- ✅ ~~`web-dom-clobbering` — DOM clobbering to bootstrap XSS~~
- ✅ ~~`web-postmessage` — cross-window `postMessage` origin flaws~~

## API
- ✅ ~~`api-versioning` — old/shadow API versions that skipped a fix~~
- `api-websocket` — realtime/subscription authz

## Mobile
- ✅ ~~`mobile-ios-assessment` — iOS static + dynamic (Frida, keychain, IPA)~~
- ✅ ~~`mobile-webview` — Android/iOS WebView JS-bridge & file-access abuse~~

## Cloud
- ✅ ~~`cloud-gcp` — GCP-specific privesc & misconfig depth~~
- ✅ ~~`cloud-azure` — Entra ID / Azure RBAC attacks~~
- ✅ ~~`cloud-docker-registry` — exposed/unauth registries and image secrets~~

## AI / LLM
- ✅ ~~`ai-llm-dos` — unbounded-consumption / cost-amplification (LLM10)~~
- ✅ ~~`ai-supply-chain` — poisoned models/datasets/plugins (LLM03/LLM05)~~

## Code review
- ✅ ~~`code-review-python`, `code-review-nodejs`, `code-review-java`, `code-review-php`,~~
  ~~`code-review-go`~~ — per-language sink/idiom guides
- ✅ ~~`code-review-iac` — Terraform/CloudFormation/K8s manifest review~~
- ✅ ~~`code-review-cicd` — pipeline & GitHub Actions security (poisoned workflows, secrets)~~

## Recon / OSINT
- ✅ ~~`recon-cloud-assets` — finding an org's cloud footprint (buckets, apps, IP ranges)~~
- ✅ ~~`recon-github-leaks` — deep GitHub/org code-leak hunting~~ (done as `recon-github-code-leaks`)

## Defense (blue team)
- ✅ ~~`defense-threat-modeling` — STRIDE/attack-tree modeling for a design~~
- ✅ ~~`defense-log-analysis` — hunting in logs (auth, web, cloud) with concrete queries~~
- ✅ ~~`defense-purple-team` — turning each offensive skill into a detection test~~

## Exploit dev / RE
- ✅ ~~`exploit-binary-basics` — intro binary exploitation workflow (pwntools)~~
  (covered by `exploit-memory-corruption`)
- ✅ ~~`re-methodology` — reverse-engineering a binary for a bug~~
  (covered by `reverse-eng-binary-triage`)

## Thin domains — depth wanted
These domains have only a handful of skills; well-scoped additions here are high-value:
- 🟢 `wireless` (2 skills) — WPA3/SAE transition-mode downgrade, 802.1X/EAP enterprise attacks,
  PMKID/deauth variations beyond `wireless-wpa2-attacks`
- `cryptography` (2 skills) — weak-randomness / nonce-reuse attacks, CBC bit-flipping, hash
  length-extension (`hashpump`)
- `privesc` (4 skills) — Windows service/ACL privesc beyond `privesc-windows-tokens`, sudo
  misconfig depth, container-host breakout from a root shell
- `network` (6 skills) — IPv6 rogue-RA/mitm6, SNMP community abuse, LLMNR/NBT-NS poisoning
- `automation` (2 skills) — CI-checked payload validation, safe headless-scan orchestration

## Proposed new domains (need a taxonomy addition — open an issue first)
- ✅ ~~`crypto`~~ — done as the `cryptography` domain
- ✅ ~~`social-engineering`~~ — done as the `social-eng` domain
- `smart-contracts` — dedicated EVM auditing domain (seeded by `code-review-solidity`; reentrancy,
  oracle manipulation, access control)

## Library / tooling
- Per-skill `references/` deep-dives (payloads, cheat-sheets) where a `SKILL.md` gets long
- A `checklist`-type skill for the domains that still lack one (see `web-testing-checklist` and
  `api-testing-checklist` as the pattern): network, cloud, mobile, ad, ai-ml
- Agent-integration hooks beyond Claude Code (see `tools/hooks/`) — e.g. a Kimi Code activity
  hook, or a generic shell-wrapper logger
- Coverage gaps: see [COVERAGE.md](COVERAGE.md) for which standards are thin

---
Want something not listed? Open an issue describing the technique and its trigger signals.
