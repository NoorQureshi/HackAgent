# Detecting Cross-Site Request Forgery (CSRF)

CSRF leaves almost no trace on the server — the request is legitimate in every field. What
gives it away is *context*: state-changing requests arriving with a cross-site `Origin`/`Referer`
and no valid anti-CSRF token.

## What to log / where it shows up
- **Web server / app logs**: `Origin` and `Referer` headers on state-changing (POST/PUT/DELETE) requests — the single most useful signal, and often not logged by default. Enable it.
- **Application logs**: anti-CSRF token validation failures (missing/mismatched token) per session.
- **Auth logs**: a state change (password/email change, payout method added) with no preceding session activity on your pages — the victim never visited your UI before the request.

## Sigma rule
```yaml
title: State-Changing Request with Cross-Site Origin and Missing CSRF Token
id: 8f8f1ae0-411a-42a8-94e2-2c603c7eed8e
status: experimental
description: Detects potential CSRF — POST/PUT/DELETE to sensitive endpoints where the Origin/Referer is external and CSRF-token validation failed or was absent.
logsource:
    category: application
    product: webapp
detection:
    selection:
        http_method:
            - 'POST'
            - 'PUT'
            - 'DELETE'
            - 'PATCH'
        csrf_token_valid: 'false'
    selection_sensitive:
        cs-uri-stem|contains:
            - '/password'
            - '/email'
            - '/settings'
            - '/profile'
            - '/transfer'
            - '/payout'
            - '/role'
            - '/delete'
    selection_origin:
        origin_is_same_site: 'false'   # enrich from Origin/Referer vs Host in your pipeline
    filter_api:
        auth_type: 'bearer'            # token-authenticated API clients don't send cookies — CSRF n/a
    condition: selection and selection_sensitive and selection_origin and not filter_api
falsepositives:
    - Legitimate third-party integrations posting to your endpoints (payment callbacks, webhooks)
    - Mobile apps or CLI clients that don't send Origin headers
level: medium
tags:
    - attack.t1204
    - cwe.352
```

## Behavioral signals
- A state change whose session shows *no prior page fetches* — no GET of the form that normally precedes the POST.
- A spike of identical sensitive requests across *many unrelated sessions* in a short window — a mass-phished CSRF landing page.
- Referer pointing at a freshly-registered or unrelated domain immediately before account-change requests.

## False positives
- Payment/SSO/webhook callbacks posting cross-origin by design — whitelist those paths; they're the endpoints attackers probe too, so tune narrowly.
- Browsers stripping Referer under `Referrer-Policy` — prefer `Origin` (present on all cross-site POSTs) over Referer for the enrichment.
