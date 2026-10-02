# Detecting SQL Injection

From the defender's side, SQLi is a burst of requests whose parameters carry SQL syntax —
quotes, comment terminators, boolean tautologies, and DB function names — often followed by
500s or abnormally slow responses from the same endpoint.

## What to log / where it shows up
- **Web server access logs** (nginx/Apache/IIS): request line + query string hold most payloads.
- **WAF logs**: the richest source — rule hits on `union select`, tautologies, `information_schema`.
- **Application logs**: DB errors (`You have an error in your SQL syntax`, `ORA-01756`, `Unclosed quotation mark`, `pg_query`) are near-conclusive when they follow a quoted param.
- **Response-time telemetry**: time-blind extraction shows as an endpoint's latency pinned to 5s/10s multiples for one source.

## Sigma rule
```yaml
title: SQL Injection Attempt in Web Request
id: 334bd6a4-1818-4971-a592-f6de12a788ed
status: experimental
description: Detects common SQL injection payload patterns in HTTP request URIs and query parameters.
logsource:
    category: webserver
detection:
    selection:
        cs-uri-query|contains:
            - "' or '"
            - "' and '"
            - ' union select'
            - ' union all select'
            - 'information_schema'
            - 'sleep('
            - 'pg_sleep'
            - 'waitfor delay'
            - 'benchmark('
            - 'load_file('
            - 'extractvalue('
            - 'updatexml('
            - 'convert(int,'
            - '--'
            - '%27'          # URL-encoded single quote
    condition: selection
falsepositives:
    - Search or query features that legitimately accept quotes and SQL-like terms
    - Security scanners and authorized pentests
level: high
tags:
    - attack.t1190
    - cwe.89
```

## Behavioral signals
- One source iterating a single parameter with `'`, `"`, `)` then `AND 1=1` / `AND 1=2` pairs — the classic detect-then-confirm sequence.
- Rising 500/DB-error rate on one endpoint from one IP or session.
- Hundreds of near-identical requests differing only in an offset/character position — boolean-blind or time-blind extraction (sqlmap's default cadence).
- Response latency for one source locked at injected-sleep durations (5s, 10s) while other clients stay fast.

## False positives
- Legit search fields that accept quotes/apostrophes (`O'Brien`) — tune by requiring multiple payload indicators or excluding known search params.
- Vulnerability scanners and authorized tests — suppress by scanner UA/IP ranges, but keep a log of what they hit.
