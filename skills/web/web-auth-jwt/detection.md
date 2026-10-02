# Detecting JWT Attacks

JWT attacks are visible in the tokens themselves: `alg:none`, algorithm confusion (`RS256`→`HS256`),
brute-forced signatures, and claims the issuer never minted — all arriving in the
`Authorization: Bearer` header.

## What to log / where it shows up
- **Application/auth logs**: signature-validation failures, `alg` mismatch errors, expired-token rejections — the attacker's probing is loud if you log validation outcomes.
- **API gateway / web logs**: full `Authorization` header capture (where policy allows) lets you decode and inspect incoming JWTs.
- **Identity provider logs**: token-issuance rate per client vs token-*presentation* rate per client — replay/forgery skews the ratio.

## Sigma rule
```yaml
title: Suspicious JWT Presented to Application
id: 00b199a6-e9de-496c-ac2c-ccc7a97a3b30
status: experimental
description: Detects JWT attack patterns in presented tokens — alg:none, algorithm confusion, kid/path-traversal injection, and unsigned or tampered payloads. Requires decoding the Bearer token in the pipeline (header.payload captured as fields).
logsource:
    category: application
    product: webapp
detection:
    selection_alg_none:
        jwt_alg:
            - 'none'
            - 'None'
            - 'NONE'
    selection_alg_confusion:
        # Token requests symmetric alg while the keyset is asymmetric (RS256/ES256 issued)
        jwt_alg|contains:
            - 'HS256'
            - 'HS384'
            - 'HS512'
        issuer_key_type: 'asymmetric'
    selection_kid_injection:
        jwt_kid|contains:
            - '../'
            - '..\\'
            - '/dev/null'
            - '|'
            - ';'
    condition: 1 of selection_*
falsepositives:
    - Legacy clients during an HS256→RS256 migration — scope by client ID and expire the exemption
    - Test/integration environments sharing log pipelines with production
level: critical
tags:
    - attack.t1550.001
    - attack.t1078
    - cwe.347
```

## Behavioral signals
- A burst of signature-validation failures from one source — secret brute-forcing against a live token or hand-crafted claims.
- Same `sub`/`iat` claim values across many tokens with only the signature changing — offline-crack attempts replayed online.
- A token whose payload claims (role, tenant, user id) don't match anything the IdP issued for that subject — comparison of presented vs issued claims catches forgery even when the signature validates (key confusion).
- Requests alternating the same endpoint with the real token then a near-identical tampered one — byte-level claim fuzzing.

## False positives
- Mobile apps with stale cached tokens (expired-signature noise) — alert on *invalid signature*, not *expired*.
- Multi-IdP setups where algs legitimately differ per tenant — key the rule to issuer, not globally.
