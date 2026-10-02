#!/usr/bin/env python3
"""SploitAgent skills maintenance script.

Scans skills/<domain>/<slug>/SKILL.md, then:
  validate      -> check every skill's frontmatter against the schema keys/enums
  catalog       -> write CATALOG.md (browsable) + data/skills_index.json + docs/skills.json
  coverage      -> write COVERAGE.md (standards mapping)
  stamp         -> rewrite hardcoded skill counts (total + per-domain) in README/docs
  check-counts  -> non-mutating guard: fail if any hardcoded count is stale (for CI)
  all           -> validate + catalog + coverage + stamp  (default)

No third-party deps: a minimal frontmatter parser handles our controlled files.
Run: python3 tools/catalog.py [validate|catalog|all]
"""
import sys, os, re, json, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")

REQUIRED = ["name", "description", "domain", "type", "stability", "modes", "schema_version"]
DOMAINS = ["recon","web","api","mobile","cloud","network","wireless","ad","ai-ml","code-review",
           "exploit-dev","reverse-engineering","cryptography","privesc","defense","payloads",
           "reporting","automation","tradecraft","social-eng"]
TYPES = ["technique","arsenal","methodology","checklist","reference"]
STABILITY = ["locked","learning"]
MODES = ["pentest","bugbounty","defense"]
DOMAIN_TITLES = {
    "recon":"Reconnaissance","web":"Web application","api":"API","mobile":"Mobile",
    "cloud":"Cloud & containers","network":"Network & services","wireless":"Wireless / Wi-Fi",
    "ad":"Active Directory",
    "ai-ml":"AI / LLM","code-review":"Source-code review","exploit-dev":"Exploit development",
    "reverse-engineering":"Reverse engineering","cryptography":"Cryptography",
    "privesc":"Privilege escalation","defense":"Defense / blue-team","payloads":"Payloads",
    "reporting":"Reporting","automation":"Automation","tradecraft":"Tradecraft & discipline",
    "social-eng":"Social engineering",
}

def parse_frontmatter(path):
    text = open(path, encoding="utf-8").read().split("\n")
    if not text or text[0].strip() != "---":
        return None
    end = None
    for i in range(1, len(text)):
        if text[i].strip() == "---":
            end = i; break
    if end is None:
        return None
    fm, i = {}, 1
    lines = text[1:end]
    j = 0
    while j < len(lines):
        line = lines[j]
        m = re.match(r'^([A-Za-z0-9_]+):\s*(.*)$', line)
        if not m:
            j += 1; continue
        key, val = m.group(1), m.group(2).strip()
        if val in (">", "|", ">-", "|-"):  # folded/literal block
            block = []
            j += 1
            while j < len(lines) and (lines[j].startswith("  ") or lines[j].strip() == ""):
                block.append(lines[j].strip()); j += 1
            fm[key] = " ".join(x for x in block if x).strip()
            continue
        if val.startswith("[") and val.endswith("]"):  # inline list
            inner = val[1:-1].strip()
            fm[key] = [x.strip() for x in inner.split(",")] if inner else []
        else:
            fm[key] = val
        j += 1
    return fm

def collect():
    skills = []
    for p in sorted(glob.glob(os.path.join(SKILLS, "*", "*", "SKILL.md"))):
        fm = parse_frontmatter(p)
        reldir = os.path.relpath(os.path.dirname(p), ROOT)
        skills.append({"path": p, "reldir": reldir, "fm": fm or {}})
    return skills

def short_desc(fm):
    d = (fm.get("description") or "").strip()
    d = re.sub(r'\s+', ' ', d)
    d = re.sub(r'^One line:\s*', '', d, flags=re.I)
    # first sentence, capped
    cut = d.find(". ")
    if 0 < cut < 160:
        return d[:cut+1]
    return (d[:150] + "…") if len(d) > 150 else d

def _lev(a, b):
    """Small Levenshtein distance for typo detection."""
    if a == b: return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + (ca != cb)))
        prev = cur
    return prev[-1]

def check_xrefs(skills):
    """Flag a backtick `skill-ref` in a body only when it's clearly a broken skill
    reference — a domain-prefixed token that isn't a real skill but is within a
    small edit distance of one (i.e. a typo or a stale name after a rename).
    Ordinary compound words (api-key, web-server) are far from any slug and ignored."""
    slugs = {os.path.basename(s["reldir"]) for s in skills}
    names = {s["fm"].get("name","") for s in skills if s["fm"].get("name")}
    valid = slugs | names | set(DOMAINS)
    prefixes = {sl.split("-")[0] for sl in slugs}
    token_re = re.compile(r'`([a-z0-9]+(?:-[a-z0-9]+)+)`')
    errors = []
    for s in skills:
        try:
            body = open(s["path"], encoding="utf-8").read()
        except OSError:
            continue
        for tok in set(token_re.findall(body)):
            if tok in valid or tok.split("-")[0] not in prefixes:
                continue
            near = min((_lev(tok, v) for v in slugs), default=99)
            if near <= 4:  # close to a real slug ⇒ almost certainly a broken ref
                closest = min(slugs, key=lambda v: _lev(tok, v))
                errors.append(f"{s['reldir']}: broken skill reference `{tok}` — did you mean `{closest}`?")
    return errors

def cmd_validate():
    skills = collect(); errors = []
    seen = {}
    for s in skills:
        fm, where = s["fm"], s["reldir"]
        if not fm:
            errors.append(f"{where}: no/invalid frontmatter"); continue
        for k in REQUIRED:
            if k not in fm:
                errors.append(f"{where}: missing '{k}'")
        n = fm.get("name","")
        if n:
            if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', n):
                errors.append(f"{where}: name '{n}' not kebab-case")
            if n in seen:
                errors.append(f"{where}: duplicate name '{n}' (also {seen[n]})")
            seen[n] = where
        if fm.get("domain") not in DOMAINS:
            errors.append(f"{where}: domain '{fm.get('domain')}' not in taxonomy")
        if fm.get("type") not in TYPES:
            errors.append(f"{where}: type '{fm.get('type')}' invalid")
        if fm.get("stability") not in STABILITY:
            errors.append(f"{where}: stability '{fm.get('stability')}' invalid")
        modes = fm.get("modes") or []
        if not isinstance(modes, list) or not modes or any(m not in MODES for m in modes):
            errors.append(f"{where}: modes {modes} invalid (subset of {MODES}, non-empty)")
        # folder domain should match declared domain (reldir = skills/<domain>/<slug>)
        parts = s["reldir"].split(os.sep)
        folder_domain = parts[1] if len(parts) > 2 else ""
        if folder_domain and fm.get("domain") and folder_domain != fm.get("domain"):
            errors.append(f"{where}: folder domain '{folder_domain}' != frontmatter domain '{fm.get('domain')}'")
    errors += check_xrefs(skills)
    if errors:
        print("SKILL VALIDATION FAILED:", file=sys.stderr)
        for e in errors: print("  - "+e, file=sys.stderr)
        return 1
    print(f"validated {len(skills)} skills — OK")
    return 0

def cmd_catalog():
    skills = collect()
    by_domain = {}
    for s in skills:
        by_domain.setdefault(s["fm"].get("domain","(none)"), []).append(s)
    # CATALOG.md
    out = ["# SploitAgent skills catalog", "",
           f"> Generated by `tools/catalog.py`. **Do not edit by hand.** {len(skills)} skills.",
           "", "For authorized security work only — pentest engagements, bug-bounty programs, and defensive use.", ""]
    for d in DOMAINS:
        items = by_domain.get(d)
        if not items: continue
        out.append(f"## {DOMAIN_TITLES.get(d,d)} (`{d}`)")
        out.append("")
        out.append("| skill | type | modes | severity | summary |")
        out.append("|---|---|---|---|---|")
        for s in sorted(items, key=lambda x: x["fm"].get("name","")):
            fm = s["fm"]
            modes = ",".join(fm.get("modes") or [])
            out.append(f"| `{fm.get('name','')}` | {fm.get('type','')} | {modes} | {fm.get('severity','')} | {short_desc(fm)} |")
        out.append("")
    open(os.path.join(ROOT,"CATALOG.md"),"w",encoding="utf-8").write("\n".join(out))
    # data/skills_index.json
    os.makedirs(os.path.join(ROOT,"data"), exist_ok=True)
    idx = [{k:s["fm"].get(k) for k in ["name","domain","type","stability","modes","severity","owasp","owasp_llm","owasp_api","mitre","cwe"]} | {"path": s["reldir"]} for s in skills]
    json.dump({"count":len(skills),"skills":idx}, open(os.path.join(ROOT,"data","skills_index.json"),"w"), indent=2)
    # docs/skills.json — powers the searchable catalog page on the site (committed, unlike data/)
    os.makedirs(os.path.join(ROOT,"docs"), exist_ok=True)
    web = [{
        "name": s["fm"].get("name",""),
        "domain": s["fm"].get("domain",""),
        "type": s["fm"].get("type",""),
        "modes": s["fm"].get("modes") or [],
        "severity": s["fm"].get("severity",""),
        "summary": short_desc(s["fm"]),
        "tags": (s["fm"].get("owasp") or []) + (s["fm"].get("owasp_llm") or [])
                + (s["fm"].get("owasp_api") or []) + (s["fm"].get("mitre") or []) + (s["fm"].get("cwe") or []),
        "path": s["reldir"],
    } for s in sorted(skills, key=lambda x: (x["fm"].get("domain",""), x["fm"].get("name","")))]
    json.dump({"count":len(skills),"generated_by":"tools/catalog.py","skills":web},
              open(os.path.join(ROOT,"docs","skills.json"),"w"), indent=1)
    print(f"  wrote CATALOG.md ({len(skills)} skills) + data/skills_index.json + docs/skills.json")
    return 0

def cmd_coverage():
    """Roll frontmatter mappings into COVERAGE.md (which standards each skill touches)."""
    skills = collect()
    def tally(field):
        m = {}
        for s in skills:
            for tag in (s["fm"].get(field) or []):
                m.setdefault(tag, []).append(s["fm"].get("name",""))
        return dict(sorted(m.items()))
    sections = [
        ("OWASP Top 10 (2021)", "owasp"),
        ("OWASP Top 10 for LLM Apps (2025)", "owasp_llm"),
        ("OWASP API Security Top 10 (2023)", "owasp_api"),
        ("MITRE ATT&CK", "mitre"),
        ("CWE", "cwe"),
    ]
    out = ["# Coverage", "",
           f"> Generated by `tools/catalog.py`. **Do not edit by hand.** {len(skills)} skills.",
           "", "How SploitAgent's skills map to industry standards — measured from each skill's",
           "frontmatter, so it stays honest as the library grows.", ""]
    # per-domain counts
    by_domain = {}
    for s in skills:
        by_domain.setdefault(s["fm"].get("domain"), 0)
        by_domain[s["fm"].get("domain")] += 1
    out += ["## Skills by domain", "", "| domain | skills |", "|---|--:|"]
    for d in DOMAINS:
        if by_domain.get(d):
            out.append(f"| `{d}` | {by_domain[d]} |")
    out.append("")
    for title, field in sections:
        t = tally(field)
        if not t:
            continue
        out += [f"## {title}", "", "| category | skills |", "|---|---|"]
        for tag, names in t.items():
            out.append(f"| `{tag}` | {', '.join('`'+n+'`' for n in sorted(set(names)))} |")
        out.append("")
    open(os.path.join(ROOT, "COVERAGE.md"), "w", encoding="utf-8").write("\n".join(out))
    print(f"  wrote COVERAGE.md")
    return 0

# Files that hardcode the skill count(s) in prose/markup. The stamper keeps them
# in sync with the actual library so the numbers can never go stale (see cmd_stamp).
STAMP_FILES = ["README.md", "AGENTS.md", "docs/USING.md", "docs/index.html", "docs/catalog.html",
               "docs/skills.html", "tools/console/index.html"]

def _stamp(apply):
    """Rewrite hardcoded skill counts (total + per-domain) from the real library.
    Each substitution is anchored on stable surrounding text so only the number
    changes. Returns the list of files whose counts were (or would be) updated.
    apply=False is a dry run for the CI/check consistency guard."""
    skills = collect()
    total = len(skills)
    by_domain = {}
    for s in skills:
        d = s["fm"].get("domain")
        by_domain[d] = by_domain.get(d, 0) + 1
    # total-count substitutions: (pattern, replacement) — \d+ is the only thing replaced
    # \s+ (not a literal space) between anchor words, so a line-wrap can't hide a stale count.
    total_subs = [
        (r'(badge/skills-)\d+(-)',                  rf'\g<1>{total}\g<2>'),   # README shields badge
        (r'(<b>)\d+(</b>\s*skills)',                rf'\g<1>{total}\g<2>'),   # docs hero badge
        (r'(A\s+library\s+of\s+)\d+(\s+security)',  rf'\g<1>{total}\g<2>'),
        (r'(binder\s+of\s+)\d+(\s+short)',          rf'\g<1>{total}\g<2>'),
        (r'(links\s+all\s+)\d+(\s+skills)',         rf'\g<1>{total}\g<2>'),
        (r'(All\s+)\d+(\s+SploitAgent\s+skills)',   rf'\g<1>{total}\g<2>'),
        (r'(All\s+)\d+(\s+skills\s+across)',        rf'\g<1>{total}\g<2>'),
        (r'(20\s+domains,\s+)\d+(\s+skills)',       rf'\g<1>{total}\g<2>'),
        (r'(Search\s+)\d+(\s+skills)',              rf'\g<1>{total}\g<2>'),
        (r'(the\s+)\d+(\s+skills\s+themselves)',    rf'\g<1>{total}\g<2>'),
        (r'\b\d+(\s+skills\s+across\s+20\s+domains)', rf'{total}\g<1>'),
        (r'\b\d+(\s+offensive\b)',                  rf'{total}\g<1>'),
        (r'\b\d+(\s+trigger-loaded)',               rf'{total}\g<1>'),
    ]
    changed = []
    for rel in STAMP_FILES:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        orig = open(p, encoding="utf-8").read()
        txt = orig
        for pat, rep in total_subs:
            txt = re.sub(pat, rep, txt)
        for d, n in by_domain.items():
            de = re.escape(d)
            txt = re.sub(rf'(\| \[`{de}`\]\(skills/{de}\) \| )\d+( \|)', rf'\g<1>{n}\g<2>', txt)  # README table
            txt = re.sub(rf'(<b>{de}</b> <span class="n">)\d+(</span>)', rf'\g<1>{n}\g<2>', txt)   # skills.html chip
            txt = re.sub(rf'(<td><code>{de}</code></td><td>)\d+(</td>)', rf'\g<1>{n}\g<2>', txt)    # skills.html row
        if txt != orig:
            changed.append(rel)
            if apply:
                open(p, "w", encoding="utf-8").write(txt)
    return changed

def cmd_stamp():
    changed = _stamp(apply=True)
    print(f"  stamped counts into {len(changed)} file(s)" + (": " + ", ".join(changed) if changed else " (already current)"))
    return 0

def cmd_check_counts():
    stale = _stamp(apply=False)
    if stale:
        print("COUNT CHECK FAILED — stale skill counts in:", file=sys.stderr)
        for f in stale:
            print("  - " + f + "  (run: python3 tools/catalog.py stamp)", file=sys.stderr)
        return 1
    print("counts consistent")
    return 0

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "all":
        return cmd_validate() or cmd_catalog() or cmd_coverage() or cmd_stamp()
    return {"catalog":cmd_catalog,"validate":cmd_validate,"coverage":cmd_coverage,
            "stamp":cmd_stamp,"check-counts":cmd_check_counts}.get(cmd, lambda:2)()

if __name__ == "__main__":
    sys.exit(main())
