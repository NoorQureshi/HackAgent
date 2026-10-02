# Detecting API Authentication Attacks

Password spraying, credential stuffing, and token brute-forcing against API auth endpoints
show up as failure-rate anomalies: many 401s/403s from one source, or one password tried
against many accounts.

## What to log / where it shows up
- **API gateway / auth service logs**: login attempts with account, source IP/ASN, user agent, and outcome — the substrate for every rule here.
- **WAF/rate-limit logs**: throttling events on `/login`, `/token`, `/oauth/token` — the attacker hitting your ceilings.
- **IdP logs** (Okta/Auth0/Entra): impossible-travel and breached-password signals layered on top.

## Sigma rule
```yaml
title: Password Spray or Credential Stuffing Against API Authentication Endpoint
id: 8d9e6cae-1579-49e9-b20f-0a0e87c8edfa
status: experimental
description: Detects high-volume failed authentication against API login/token endpoints from a single source, spread across many distinct accounts (spray) or many attempts per account (stuffing/brute-force).
logsource:
    category: application
    product: api
detection:
    selection:
        cs-uri-stem|contains:
            - '/login'
            - '/signin'
            - '/auth'
            - '/oauth/token'
            - '/token'
        sc-status:
            - 401
            - 403
    condition: selection
    # Correlate: alert when (count of failures by source > 30 in 5 min) OR
    # (count distinct usernames by source > 10 in 5 min). Implement thresholding in the SIEM.
falsepositives:
    - Broken integrations and misconfigured service accounts hammering a rotated credential
    - Mobile clients retrying expired sessions in a reconnect storm
level: high
tags:
    - attack.t1110
    - attack.t1110.003
    - attack.t1110.004
    - owaspapi.api2
```

## Behavioral signals
- Many distinct usernames, few attempts each, one password pattern — spray. Few accounts, many attempts — brute-force. The username/password ratio is the discriminator.
- Rotating source IPs at fixed cadence (one attempt per IP per minute) — proxy-pool spray designed to sit under per-IP thresholds; aggregate by fingerprint (UA, TLS/JA3, timing).
- Lockout spikes across the directory without an incident — spray causing collateral damage.
- Successes mixed into a failure storm from unrelated residential ASNs — stuffing hits landing; alert on *any* success from an IP with a high failure history.

## False positives
- Load balancers collapsing many users behind one egress IP (corporate NAT, carrier-grade NAT) — count distinct accounts per source, not just volume.
- Scheduled jobs with expired credentials — they hammer one account at a perfect interval; suppress by exact service account.
