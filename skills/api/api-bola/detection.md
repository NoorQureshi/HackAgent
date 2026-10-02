# Detecting Broken Object Level Authorization (BOLA)

BOLA is IDOR at the API layer: a valid token asking for objects it doesn't own. Every request
looks syntactically legitimate — the only tell is the *relationship* between the caller and the
object, which means your logs must record both.

## What to log / where it shows up
- **API gateway / app logs**: caller identity (subject from the token), the object ID requested, and — critically — the object's owner. Without owner resolution at log time, BOLA is invisible after the fact.
- **Authorization decision logs**: if your authz layer (OPA, in-app checks) logs allow/deny, *allows* on foreign objects are the signal; *deny bursts* are the probing.
- **Response telemetry**: one token pulling response volume far above its account's data footprint.

## Sigma rule
```yaml
title: API Object Access by Non-Owner (BOLA)
id: 8718cb78-4220-4e38-bbc3-4a266f777d16
status: experimental
description: Detects an authenticated API caller successfully accessing objects owned by a different principal — requires owner attribution logged per request.
logsource:
    category: application
    product: api
detection:
    selection:
        http_method:
            - 'GET'
            - 'PUT'
            - 'PATCH'
            - 'DELETE'
        object_owner_equals_subject: 'false'   # enrich: resolve object owner at request time
        sc-status:
            - 200
            - 201
    filter_admin:
        caller_role:
            - 'admin'
            - 'support'      # scope tightly — admin impersonation tooling is the classic FP
    filter_internal:
        caller_is_service_account: 'true'
    condition: selection and not 1 of filter_*
falsepositives:
    - Support/admin tooling acting on behalf of users — whitelist tooling identities, but audit their volume
    - Shared/team-owned resources where ownership is legitimately plural
level: high
tags:
    - attack.t1190
    - cwe.639
    - cwe.862
    - owaspapi.api1
```

## Behavioral signals
- One token enumerating sequential object IDs (`/users/1001`…`/users/1400`) at machine cadence — humans navigate, they don't sweep ranges.
- Deny-then-allow pivot: 403s on a resource type, then 200s after the caller switches endpoint version or method (authz inconsistent across routes).
- A single session accessing objects across many tenants/customers — cross-tenant sweep.
- UUID-guessing is rare in practice; watch instead for *predictable* IDs (integers, short hashes) being walked.

## False positives
- Admin/support access is the big one — without a separate audited impersonation path, this rule drowns in it. Give support tooling its own identity and alert on anything else.
- Public/unauthenticated objects served with 200 — scope the rule to endpoints that require auth and have an owner concept.
