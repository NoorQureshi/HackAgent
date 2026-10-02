# Detecting HTTP Request Smuggling

Desync attacks barely exist in any single log — the front-end and back-end each see a
*different* request. Detection lives in the disagreement: mismatched CL/TE headers on the wire,
and victims' requests arriving with prefixes they never sent.

## What to log / where it shows up
- **Load balancer / CDN logs vs origin access logs**: request counts, paths, and headers *differing between tiers* — the defining artifact. Log `Content-Length` and `Transfer-Encoding` verbatim at both.
- **WAF logs**: requests carrying both `Content-Length` and `Transfer-Encoding`, obfuscated TE values (`Transfer-Encoding : chunked`, `Transfer-Encoding: xchunked`, `chunked\r\n` variants).
- **Application logs**: requests containing smuggled prefixes — a victim's GET whose logged path is prepended with another request's fragment, or a 404 for a path that concatenates two requests.
- **Response anomalies**: users receiving responses meant for others (cache poisoning fallout).

## Sigma rule
```yaml
title: Ambiguous Content-Length and Transfer-Encoding Headers
id: 94aead42-d0c5-4a23-b2d4-da31c4307674
status: experimental
description: Detects requests carrying both Content-Length and Transfer-Encoding, or obfuscated Transfer-Encoding values — the precondition for HTTP request smuggling (CL.TE/TE.CL/TE.TE).
logsource:
    category: webserver
detection:
    selection_both:
        has_content_length: 'true'
        has_transfer_encoding: 'true'    # requires logging both headers; enrich in pipeline
    selection_obfuscated:
        transfer_encoding|re: '(?i)(chunked[\s\S]{0,3}chunked|xchunked|chunked[,; ]|[\x0b\x0c]chunked|chunked[\x0b\x0c])'
    filter_h2:
        http_version: '2'                # HTTP/2 has no TE framing; H2 desync needs separate logic
    condition: (selection_both or selection_obfuscated) and not filter_h2
falsepositives:
    - Broken legacy clients sending both headers benignly (rare — RFC 7230 says reject these)
    - Some monitoring/synthetic tools with sloppy header handling
level: high
tags:
    - attack.t1190
    - cwe.444
```

## Behavioral signals
- Timing probes: one client sending requests whose responses stall exactly the CL/TE differential (the safe-detection delay technique) — latency outliers on one connection.
- Front-end logged N requests, origin logged N+k on the same connection window — request-count desync between tiers.
- A user's session suddenly issuing requests containing *another* user's cookies/headers in the logged path or body — request capture in flight.
- Cache entries for static assets returning attacker-controlled content after a burst of odd requests from one client.

## False positives
- Comparing tiers is noisy by nature — clock skew and sampling gaps fake desync; correlate on connection ID / TCP 5-tuple, not just time windows.
- Old HTTP/1.0 clients and broken middleware produce both-headers benignly — alert, don't block, until the pattern clusters by client.
