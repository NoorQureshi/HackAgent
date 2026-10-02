# Detecting XML External Entity (XXE) Injection

XXE is visible in the request body: a `<!DOCTYPE` declaration with an `<!ENTITY` pointing at a
file path or URL, arriving at an endpoint that parses XML — plus the server's outbound fetches
when an entity resolves.

## What to log / where it shows up
- **Application logs / request bodies**: XML payloads are usually POSTed, so access logs miss them — you need body capture or WAF inspection for `<!DOCTYPE`, `<!ENTITY`, `SYSTEM`.
- **WAF logs**: rules matching DTD declarations and `file://`/`php://filter` URIs.
- **Egress logs from the app tier**: the XML parser fetching external entities (HTTP/DNS to attacker hosts) — the OOB variant only shows here.
- **Error logs**: XML parser errors (`SAXParseException`, `lxml.etree.XMLSyntaxError`, `SimpleXMLElement`) naming files like `/etc/passwd` in the message.

## Sigma rule
```yaml
title: XXE Payload in XML Request Body
id: 912322b5-0477-4b02-be11-32e9ce42a519
status: experimental
description: Detects XML External Entity attack patterns — DOCTYPE/ENTITY declarations with external SYSTEM identifiers — in request bodies sent to XML endpoints.
logsource:
    category: application
    product: webapp
detection:
    selection_doctype:
        request_body|contains:
            - '<!DOCTYPE'
            - '<!ENTITY'
    selection_external:
        request_body|contains:
            - 'SYSTEM "file:'
            - "SYSTEM 'file:"
            - 'SYSTEM "http'
            - "SYSTEM 'http"
            - 'SYSTEM "ftp:'
            - 'php://filter'
            - 'expect://'
            - 'jar://'
    filter_benign_dtd:
        # Internal integrations that legitimately reference known DTDs
        request_body|contains:
            - 'SYSTEM "http://schemas.yourcompany.example/'
    condition: selection_doctype and selection_external and not filter_benign_dtd
falsepositives:
    - Legacy B2B/SOAP integrations that legitimately use DTDs — inventory them and whitelist exact SYSTEM URIs
    - SAML/SSO flows carrying signed XML (metadata, assertions) — usually no DOCTYPE; tune if your IdP differs
level: high
tags:
    - attack.t1190
    - cwe.611
```

## Behavioral signals
- Probing sequence: benign XML → DOCTYPE with internal entity → `file:///etc/passwd` → parameterized/DTD-hosted OOB exfil — all from one client against one endpoint.
- The app server making a DNS or HTTP fetch to an attacker domain immediately after an XML POST — blind XXE exfiltration in flight.
- `php://filter/convert.base64-encode` in a body — a near-unambiguous exfil primitive on PHP stacks.

## False positives
- SOAP/legacy integrations with real DTDs — the correct long-term fix is disabling DTD processing in the parser; until then, whitelist by exact SYSTEM URI, never by client IP alone.
- SAML assertions — signed XML without DOCTYPE shouldn't trip the rule; if it does, exempt the SSO endpoints.
