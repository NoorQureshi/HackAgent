#!/usr/bin/env python3
"""SploitAgent skills maintenance script.

Scans skills/<domain>/<slug>/SKILL.md, then:
  validate      -> check every skill's frontmatter against the schema keys/enums
  catalog       -> write CATALOG.md (browsable) + data/skills_index.json + docs/skills.json
  coverage      -> write COVERAGE.md (standards mapping)
  routing       -> write data/routing.json (per-skill trigger utterances + keywords)
  stamp         -> rewrite hardcoded skill counts (total + per-domain) in README/docs
  check-counts  -> non-mutating guard: fail if any hardcoded count is stale (for CI)
  all           -> validate + catalog + coverage + routing + stamp  (default)

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

# ---------------------------------------------------------------------------
# Routing table (data/routing.json): per-skill trigger utterances + keywords,
# distilled from each skill's description line. The matcher that consumes this
# file is documented and regression-tested in tools/test_routing.py.

# Common English function words excluded from generated keywords/triggers.
# (The matcher itself needs no stopword list — idf weighting neutralizes them.)
ROUTING_STOPWORDS = set("""
a an the and or of to in on for with without from by at as is are was were be been being it its this that these
those you your we our they their he she his her me my him them us what which who whom how when where why can
could should would may might must do does did done have has had having not no nor but if then than so such too
very just also into over under again once only own same each few more most other some any all both between
through during before after above below up down out off here there per vs etc about against within across based
will get got take takes make makes use used using keep keeps real full fast end
""".split())

# Imperative verbs stripped when a description clause becomes a task utterance.
ROUTING_LEAD_VERBS = set("""
attack abuse test exploit find detect assess review audit bypass escalate extract forge crack break use map
build perform identify discover enumerate steal coerce force pass request recover turn get run write hunt choose
decide avoid understand establish structure model plan stand trick send claim defeat peel register combine inject
overwrite poison assign validate chain move mine kill make reverse measure speak harden work fuzz respond acquire
convert triage analyze escape
""".split())

# Leading filler stripped alongside lead verbs when shaping an utterance.
_ROUTING_LEAD_FILLER = {"a", "an", "the", "one", "your", "their", "its", "our", "this", "that",
                        "security", "systematic", "of", "and", "against", "or", "for", "to", "with",
                        "into", "how", "then", "offensively", "legitimately", "productively", "safely",
                        "passively"}

# Words that start a purpose tail ("...to escalate to Domain Admin") — clip there.
_ROUTING_PURPOSE = {"to", "so", "via", "into", "without", "that", "which", "when", "until", "while", "for", "and", "or", "after"}

# Dangling trailing words clipped after truncation ("...you can run or").
_ROUTING_TRAIL_JUNK = _ROUTING_PURPOSE | {"a", "an", "the", "of", "with", "by", "in", "on", "at", "as",
                                          "using", "per", "your", "their", "its", "our", "from"}

# Hand-tuned utterances for the flagship skills; everything else is derived from
# the description line by _routing_triggers. Curated entries must still
# round-trip through the matcher — tools/test_routing.py enforces that.
CURATED_TRIGGERS = {
    "web-auth-jwt": ["is this jwt forgeable", "test the login token signature", "jwt none alg attack"],
    "web-xss": ["reflected xss in the search box", "prove stored cross-site scripting", "dom xss sink"],
    "web-sqli": ["test the id parameter for sql injection", "time-based blind sqli", "union select column extraction"],
    "web-ssrf": ["make the server fetch an internal url", "server-side request forgery probe", "ssrf to the internal network"],
    "web-idor": ["change the user id and read another account", "idor on the invoice endpoint", "insecure direct object reference"],
    "web-csrf": ["forge a state-changing request as the victim", "csrf on the email change form", "cross-site request forgery"],
    "web-ssti": ["template injection in the greeting field", "{{7*7}} renders 49", "ssti to rce"],
    "web-xxe": ["xml external entity file read", "xxe in the upload parser", "dtd entity injection"],
    "web-lfi-path-traversal": ["read /etc/passwd through the page param", "lfi to log poisoning", "path traversal dot dot slash"],
    "web-command-injection": ["user input reaches a shell", "os command injection in the ping field", "inject commands with a semicolon"],
    "web-file-upload": ["upload a webshell past the filter", "file upload to rce", "svg upload gives stored xss"],
    "web-deserialization": ["java deserialization gadget chain", "unserialize object injection", "insecure deserialization to rce"],
    "web-open-redirect": ["redirect param to an attacker site", "open redirect in the login return url", "unvalidated redirect chaining"],
    "web-oauth": ["oauth redirect_uri manipulation", "steal the authorization code", "oidc state parameter missing"],
    "web-saml": ["saml signature wrapping xsw", "unsigned assertion accepted", "forge a saml response"],
    "web-request-smuggling": ["http request smuggling cl.te", "desync the front-end and back-end", "te.cl smuggle a request past the waf"],
    "web-cache-poisoning": ["poison the shared cache with an unkeyed header", "web cache poisoning via x-forwarded-host", "cache serves my content to everyone"],
    "web-cache-deception": ["trick the cdn into caching a private page", "cache deception on the account page", "victim profile cached at a public url"],
    "web-cors": ["cors reflects an arbitrary origin", "read cross-origin responses with credentials", "cors misconfig data theft"],
    "web-csp-bypass": ["bypass the content-security-policy", "script runs despite csp", "csp nonce reuse"],
    "web-clickjacking": ["frame the settings page invisibly", "clickjacking the delete button", "ui redress attack"],
    "web-prototype-pollution": ["pollute object.prototype", "client-side prototype pollution to xss", "__proto__ in the query string"],
    "web-race-conditions": ["fire parallel requests to double-spend", "race condition on the coupon endpoint", "toctou single-use token reused"],
    "web-mfa-bypass": ["bypass the otp step", "totp brute force with no rate limit", "skip the second factor"],
    "web-account-takeover": ["take over an account via password reset", "ato through the email change flow", "reset token is predictable"],
    "web-websocket": ["cross-site websocket hijacking cswsh", "tamper websocket messages", "ws endpoint missing auth"],
    "web-subdomain-takeover": ["dangling cname to an unclaimed service", "subdomain takeover on the old host", "claim the orphaned dns record"],
    "web-business-logic": ["abuse the checkout flow logic", "negative quantity in the cart", "business logic flaw skips payment"],
    "web-host-header": ["host header injection poisons reset links", "x-forwarded-host cache abuse", "password reset link points to my domain"],
    "web-testing-checklist": ["systematic web app testing checklist", "what to test on this web application", "web pentest coverage checklist"],
    "api-testing-checklist": ["systematic api testing checklist", "what to test on this rest api", "api assessment coverage checklist"],
    "api-graphql": ["introspection enabled on the graphql endpoint", "graphql batching abuse", "deeply nested query dos"],
    "api-bola": ["bola on the rest api", "read another user's object by id", "broken object level authorization"],
    "api-mass-assignment": ["add role admin to the json body", "mass assignment privilege escalation", "auto-binding extra fields"],
    "cloud-s3-exposure": ["is this s3 bucket public", "list the exposed bucket anonymously", "azure blob open to everyone"],
    "cloud-kubernetes": ["exposed kubelet api", "kubernetes dashboard unauthenticated", "etcd readable from a pod"],
    "cloud-imds-ssrf": ["steal instance metadata credentials", "imdsv1 reached through ssrf", "169.254.169.254 from the app"],
    "cloud-container-escape": ["break out of the container to the host", "privileged container escape", "escape the pod to the node"],
    "cloud-docker-api-abuse": ["docker api on 2375 unauthenticated", "abuse the exposed docker daemon", "docker.sock mounted in the container"],
    "cloud-iam-privesc": ["escalate aws iam from read-only", "iam privilege escalation path", "passrole abuse"],
    "ad-kerberoasting": ["kerberoast the service accounts", "as-rep roast users without preauth", "crack the tgs tickets offline"],
    "ad-adcs": ["esc1 certificate template misconfig", "adcs escalation to domain admin", "abuse the certificate authority"],
    "network-ntlm-relay": ["relay ntlm auth to smb", "coerce and relay authentication", "ntlm relay to ldap"],
    "network-password-spraying": ["spray one password across all users", "password spraying without lockouts", "stuff breached creds against the portal"],
    "network-credential-cracking": ["crack this ntlm hash", "which hashcat mode for this hash", "john wordlist and rules for the capture"],
    "network-pivoting-tunneling": ["pivot into the internal network", "socks proxy through the foothold", "port forward through the jump host"],
    "ai-prompt-injection": ["prompt injection in the chatbot", "indirect injection through a web page", "make the llm ignore its instructions"],
    "ai-jailbreak": ["jailbreak the llm's guardrails", "bypass the model's safety policy", "make it produce restricted output"],
    "ai-rag-poisoning": ["poison the rag knowledge base", "planted document hijacks retrieval", "poisoned content the model retrieves"],
    "ai-mcp-security": ["audit this mcp server", "tool poisoning in the mcp tool list", "prompt injection through tool results"],
    "recon-subdomain-enum": ["enumerate subdomains for the program", "find live hosts in scope", "subdomain brute force and permutations"],
    "recon-osint": ["passive osint on the target org", "google dorks for exposed files", "shodan recon without touching the target"],
    "privesc-linux-gtfobins": ["suid binary privesc via gtfobins", "sudo rule lets me escalate", "abuse capabilities to get root"],
    "privesc-windows-tokens": ["seimpersonate potato privesc", "token impersonation to system", "potato family escalation"],
    "payloads-reverse-shells": ["get a reverse shell on the target", "upgrade to a fully interactive tty", "bind shell payload that works"],
    "crypto-oracle-attacks": ["padding oracle on the cookie", "decrypt the token without the key", "cbc bit-flipping forgery"],
    "mobile-cert-pinning-bypass": ["bypass certificate pinning on the app", "frida unpinning to proxy traffic", "ssl pinning blocks burp"],
    "wireless-wpa2-attacks": ["capture the wpa2 handshake", "pmkid attack with no clients", "crack the wifi psk offline"],
    "wireless-evil-twin": ["stand up an evil twin ap", "rogue captive portal harvests credentials", "peap mschapv2 challenge capture"],
    "ad-pivot-arsenal": ["arsenal of ad pivoting and cracking tools", "password cracking tool arsenal", "which tools for ad post-exploitation"],
    "ai-agent-tool-abuse": ["make the llm agent call tools with bad args", "tool abuse through the agent's functions", "coerce the agent into ssrf or exfil"],
    "code-review-cpp": ["review this c/c++ code for memory safety", "cpp unsafe api sinks", "buffer overflow in the c source"],
    "code-review-python": ["review this python code for security bugs", "django and flask dangerous sinks", "security review of the python codebase"],
    "code-review-secrets-detection": ["find leaked secrets in the git history", "api keys committed to the repo", "scan ci logs for leaked credentials"],
    "defense-log-analysis": ["hunt attacker activity in the logs", "what to look for in auth logs", "siem queries for suspicious logons"],
    "recon-content-discovery": ["find hidden paths on the web target", "brute force directories and files", "content discovery with wordlists"],
    "recon-js-analysis": ["mine the javascript for secrets", "endpoints hidden in the js bundles", "extract api routes from frontend js"],
    "defense-incident-response": ["run the incident response process", "contain and eradicate the intrusion", "ir playbook for this breach"],
    "crypto-rsa-attacks": ["break rsa with weak parameters", "recover the private key from the public key", "rsa padding attack"],
    "api-fuzzing": ["fuzz the api endpoints systematically", "enumerate api methods and params", "ffuf the api for hidden endpoints"],
    "defense-detection-sigma": ["write a sigma rule for this behavior", "convert sigma rules to our siem", "portable detections mapped to att&ck"],
    "social-eng-phishing": ["phishing campaign for the client's employees", "spear-phishing assessment with a landing page", "measure the click rate safely"],
}

def _rtokens(text):
    """Routing tokens: lowercase alnum runs minus stopwords and 1-char tokens
    (except 'c', needed by code-review-cpp)."""
    return [t for t in re.findall(r"[a-z0-9]+", text.lower())
            if (len(t) > 1 or t == "c") and t not in ROUTING_STOPWORDS]

def _routing_clauses(desc):
    """Split a description into utterance-shaped clauses: cut on punctuation,
    strip a leading imperative verb/article, clip purpose tails."""
    out = []
    for part in re.split(r"\s+[—–]\s+|,\s*|;\s*|\(|\)|\s+→\s+|:\s+", desc):
        words = part.split()
        while words and (words[0].lower().strip(".,") in ROUTING_LEAD_VERBS
                         or words[0].lower() in _ROUTING_LEAD_FILLER):
            words = words[1:]
        for i, w in enumerate(words):
            if i >= 2 and w.lower().strip(".,") in _ROUTING_PURPOSE:
                words = words[:i]
                break
        words = words[:8]
        while words and words[-1].lower().strip(".,") in _ROUTING_TRAIL_JUNK:
            words = words[:-1]
        u = " ".join(words).strip(" .,;:—–-/&").lower()
        if "…" not in u and _rtokens(u):
            out.append(u)
    return out

def _routing_disc_tokens(name, desc, df):
    """The skill's distinct tokens, most library-rare first (stable on ties) —
    the discriminative core used for keywords and the keyword-style trigger."""
    seen, ordered = set(), []
    for t in _rtokens(name.replace("-", " ") + " " + desc):
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return sorted(ordered, key=lambda t: (df.get(t, 0), ordered.index(t)))

def _routing_triggers(name, desc, df):
    """2–4 deterministic triggers per skill: a 'test for <head clause>'
    utterance, a second clause that carries a library-rare token (a bare
    keyword-style utterance), and a pure-keyword query from the rarest tokens.
    df = document frequency of tokens across all skills."""
    if name in CURATED_TRIGGERS:
        return list(CURATED_TRIGGERS[name])
    disc = _routing_disc_tokens(name, desc, df)
    clauses = _routing_clauses(desc)
    head = clauses[0] if clauses else ""
    rare = [c for c in clauses[1:]
            if min((df.get(t, 0) for t in set(_rtokens(c))), default=99) <= 3]
    rare.sort(key=lambda u: sum(df.get(t, 0) for t in set(_rtokens(u))))
    triggers = []
    if head:
        triggers.append("test for " + head)
    if rare:
        triggers.append(rare[0])
    elif head:
        triggers.append("check " + head)
    if disc:
        triggers.append(" ".join(disc[:3]))
    while len(triggers) < 2:
        triggers.append(name.replace("-", " "))
    out = []
    for t in triggers:
        if t and t not in out:
            out.append(t)
    return out[:4]

def cmd_routing():
    """Write data/routing.json — committed trigger/keyword table for routing a
    task utterance to a skill. Deterministic: sorted skills, no timestamps."""
    skills = collect()
    df = {}
    descs = {}  # name -> description with the 150-char cap's partial last word dropped
    for s in skills:
        name = s["fm"].get("name", "")
        descs[name] = re.sub(r"\S*…$", "", short_desc(s["fm"])).strip()
        for t in set(_rtokens(name.replace("-", " ") + " " + descs[name])):
            df[t] = df.get(t, 0) + 1
    entries = []
    for s in sorted(skills, key=lambda x: x["fm"].get("name", "")):
        fm = s["fm"]
        name = fm.get("name", "")
        desc = descs.get(name, "")
        entries.append({"slug": name, "domain": fm.get("domain", ""),
                        "triggers": _routing_triggers(name, desc, df),
                        "keywords": _routing_disc_tokens(name, desc, df)[:16]})
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    payload = {"count": len(entries), "generated_by": "tools/catalog.py routing",
               "matcher": "token-idf overlap — documented in tools/test_routing.py",
               "skills": entries}
    with open(os.path.join(ROOT, "data", "routing.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=True)
        f.write("\n")
    n = sum(len(e["triggers"]) for e in entries)
    print(f"  wrote data/routing.json ({len(entries)} skills, {n} triggers)")
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
        return cmd_validate() or cmd_catalog() or cmd_coverage() or cmd_routing() or cmd_stamp()
    return {"catalog":cmd_catalog,"validate":cmd_validate,"coverage":cmd_coverage,
            "routing":cmd_routing,"stamp":cmd_stamp,"check-counts":cmd_check_counts}.get(cmd, lambda:2)()

if __name__ == "__main__":
    sys.exit(main())
