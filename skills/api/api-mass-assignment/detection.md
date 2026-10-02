# Detecting Mass Assignment

Mass assignment is a client sending fields the UI never offered: `role`, `is_admin`, `balance`
in a request body. The attack is only visible if you log what was *submitted* versus what the
schema allows.

## What to log / where it shows up
- **Application logs**: full request bodies (or at least key names) on create/update endpoints — the extra fields are the whole signal.
- **Schema-validation logs**: if your framework rejects unknown properties, log the rejections — attack attempts arrive as validation errors naming privileged fields.
- **Audit/change logs**: privileged attributes (`role`, `verified`, `credits`, `tenant_id`) changing without an admin-initiated workflow.

## Sigma rule
```yaml
title: Mass Assignment — Privileged Field in Client-Supplied Request Body
id: 9ecb1cfa-0beb-422a-a19a-f5a11e255c04
status: experimental
description: Detects privileged or internal model attributes appearing in client-supplied JSON bodies on create/update endpoints — the signature of mass assignment attempts.
logsource:
    category: application
    product: api
detection:
    selection:
        http_method:
            - 'POST'
            - 'PUT'
            - 'PATCH'
        request_body|contains:
            - '"role"'
            - '"is_admin"'
            - '"isAdmin"'
            - '"admin"'
            - '"is_verified"'
            - '"verified"'
            - '"balance"'
            - '"credits"'
            - '"permissions"'
            - '"tenant_id"'
            - '"organization_id"'
            - '"price"'
    filter_admin_paths:
        cs-uri-stem|startswith:
            - '/admin/'
            - '/internal/'
    filter_payment:
        cs-uri-stem|contains: '/checkout'     # price is legitimate client input on some flows
    condition: selection and not 1 of filter_*
falsepositives:
    - Admin consoles legitimately setting these fields (exempt the admin route prefix, not the field names)
    - Public signup flows that accept a `role` choice (tenant vs user) — tune to that exact endpoint
level: high
tags:
    - attack.t1190
    - cwe.915
    - owaspapi.api3
```

## Behavioral signals
- A client replaying the same update request while adding one new field each time — field-name probing copied from the app's own GET response shape.
- Attempts immediately following a `GET` of the same object — the attacker mirrors the response schema back into the write (response-to-request reflection).
- Multiple clients hitting a freshly-launched endpoint with `is_admin` probes within days of release — bug-bounty hunters find new surface fast.
- Privileged-attribute change in audit logs with no corresponding admin action in the admin-console logs — successful exploitation.

## False positives
- Admin APIs share field names with user APIs — scope by path prefix and caller role, never suppress the field list globally.
- API docs/client SDKs that expose internal fields — if the SDK sends `role` routinely, that's a design bug; flag it rather than tuning the rule away.
