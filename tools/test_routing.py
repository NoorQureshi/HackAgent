#!/usr/bin/env python3
"""Routing regression suite for data/routing.json.

THE MATCHER (this is the whole algorithm — a scoring heuristic, not ML):
  1. Tokenize: lowercase, split on non-alphanumeric runs ([a-z0-9]+). No
     stopword list, no stemming — corpus weighting (step 3) neutralizes filler
     words like "test"/"the" because they appear in nearly every document.
  2. Each skill's document = the tokens of its trigger utterances plus its
     precomputed `keywords` (library-rare tokens distilled from the skill's
     description by `tools/catalog.py routing`).
  3. df(t) = number of skill documents containing token t;
     idf(t) = ln(1 + N / df(t)) — rare tokens dominate the score.
  4. score(query, skill) = sum of idf(t) over query tokens present in the
     skill's document. Route to the single highest-scoring skill; a tie or an
     all-zero result is a routing failure.

An integration routes a user/agent utterance exactly this way: load
data/routing.json, build the index once, score, take the argmax.

Checks: no duplicate slugs, the table matches the skills on disk, each skill
has 2–4 distinct triggers, and every trigger round-trips to its own skill with
a unique best score (no ties). Exits non-zero with a readable failure list.

Allowlist: ROUTING_ALLOW maps "slug|trigger" -> reason for known-unroutable
cases. Keep it empty — fix the trigger or the matcher instead.
"""
import sys, os, re, json, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from catalog import collect  # ground truth: which skills exist on disk

ROUTING_JSON = os.path.join(ROOT, "data", "routing.json")
ROUTING_ALLOW = {}  # "slug|trigger" -> reason (see docstring; aim for zero)

def tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())

def build_index(skills):
    docs, df = {}, {}
    for s in skills:
        doc = set(s.get("keywords") or [])
        for tr in s.get("triggers") or []:
            doc |= set(tokens(tr))
        docs[s["slug"]] = doc
        for t in doc:
            df[t] = df.get(t, 0) + 1
    n = len(docs)
    return docs, {t: math.log(1 + n / c) for t, c in df.items()}

def route(query, docs, idf):
    """Return (best_slug, tied) — tied=True when another skill shares the top score."""
    q = set(tokens(query))
    best, best_score, tied = None, 0.0, False
    for slug, doc in docs.items():
        sc = sum(idf[t] for t in q if t in doc)
        if sc > best_score + 1e-9:
            best, best_score, tied = slug, sc, False
        elif sc > 1e-9 and abs(sc - best_score) <= 1e-9:
            tied = True
    return best, tied

def main():
    failures = []
    try:
        table = json.load(open(ROUTING_JSON, encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"ROUTING TEST FAILED: cannot read {os.path.relpath(ROUTING_JSON, ROOT)}: {e}\n"
              "  run: python3 tools/catalog.py routing", file=sys.stderr)
        return 1
    skills = table.get("skills") or []

    # structural checks
    slugs = [s.get("slug", "") for s in skills]
    for slug in sorted(set(slugs)):
        if slugs.count(slug) > 1:
            failures.append(f"duplicate slug in routing.json: {slug}")
    on_disk = {}  # name -> (domain, reldir)
    for s in collect():
        fm = s["fm"]
        on_disk[fm.get("name", "")] = (fm.get("domain", ""), s["reldir"])
    for slug in sorted(set(slugs) - set(on_disk)):
        failures.append(f"routing.json has '{slug}' but no such skill on disk (regenerate: catalog.py routing)")
    for slug in sorted(set(on_disk) - set(slugs)):
        failures.append(f"skill '{slug}' missing from routing.json (regenerate: catalog.py routing)")
    for s in skills:
        slug = s.get("slug", "?")
        dom = s.get("domain", "")
        if slug in on_disk and dom != on_disk[slug][0]:
            failures.append(f"{slug}: domain '{dom}' != on-disk '{on_disk[slug][0]}'")
        trg = s.get("triggers") or []
        if not 2 <= len(trg) <= 4:
            failures.append(f"{slug}: has {len(trg)} triggers (need 2-4)")
        if len(set(trg)) != len(trg):
            failures.append(f"{slug}: duplicate triggers {trg}")
    if failures:
        print(f"ROUTING TEST FAILED ({len(failures)} structural problems):", file=sys.stderr)
        for f in failures:
            print("  - " + f, file=sys.stderr)
        return 1

    # round-trip: every trigger must route back to its own skill, tie-free
    docs, idf = build_index(skills)
    cases = 0
    for s in skills:
        for trg in s["triggers"]:
            key = f"{s['slug']}|{trg}"
            if key in ROUTING_ALLOW:
                continue
            cases += 1
            best, tied = route(trg, docs, idf)
            if best != s["slug"]:
                failures.append(f"{s['slug']}: trigger {trg!r} routes to {best!r}")
            elif tied:
                failures.append(f"{s['slug']}: trigger {trg!r} ties with another skill")
    if failures:
        print(f"ROUTING TEST FAILED ({len(failures)}/{cases} cases):", file=sys.stderr)
        for f in failures:
            print("  - " + f, file=sys.stderr)
        return 1
    print(f"routing OK — {len(skills)} skills, {cases} trigger cases, all round-trip with unique winners")
    return 0

if __name__ == "__main__":
    sys.exit(main())
