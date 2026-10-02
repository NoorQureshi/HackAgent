# Detecting Insecure Direct Object Reference (IDOR)

IDOR rarely looks malicious in a single log line — it's a *pattern*: one authenticated session
walking object IDs (`id=1,2,3...`) and pulling records belonging to other users, all with
200 responses.

## What to log / where it shows up
- **Application logs** (essential): you need the authenticated user ID *and* the object ID/owner per request — access logs alone can't distinguish IDOR from normal use.
- **API gateway logs**: per-user request rates per endpoint, with path parameters extracted.
- **Response-size telemetry**: an account downloading far more objects than it owns shows as response volume 100× baseline for that endpoint.

## Sigma rule
```yaml
title: Horizontal Object Enumeration via Sequential Identifier Access
id: 646b1109-0e5d-4df4-9185-c8834b7de412
status: experimental
description: Detects a single authenticated principal accessing many distinct numeric object IDs on one endpoint — the signature of IDOR/BOLA enumeration.
logsource:
    category: webserver
detection:
    selection:
        cs-method: 'GET'
        cs-uri-stem|re: '/(api/)?(v[0-9]+/)?(users?|accounts?|orders?|invoices?|documents?|tickets?|profiles?)/[0-9]+'
        sc-status:
            - 200
    condition: selection
    # Correlate: alert when count(distinct object id) by (user/session) > 50 within 10 minutes.
    # Sigma has no native thresholding — implement the aggregation in your SIEM.
falsepositives:
    - Admin/support tooling and dashboards that legitimately browse many records
    - Pagination through a user's *own* list (same owner — tune on owner != requester, not volume)
level: medium
tags:
    - attack.t1190
    - cwe.639
    - owaspapi.api1
```

## Behavioral signals
- Sequential or tightly-clustered object IDs from one session — humans click links; they don't request `/invoice/10431` through `/invoice/10530` in order.
- ID sweep that pauses and slows after the first 403 — the tester finding the authorization boundary and working around it.
- One account pulling objects at machine cadence (sub-second, perfectly regular intervals) on a UI endpoint normally browsed at human speed.
- Referer missing or mismatched — requests arriving directly rather than through the app's own navigation flow.

## False positives
- Admin panels and support consoles that genuinely enumerate records — exempt known tooling identities, alert when a *customer* account does it.
- Legitimate bulk-export features — distinguish by endpoint: export APIs paginate; IDOR walks single-object endpoints.
