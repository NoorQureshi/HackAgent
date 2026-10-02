# Detecting Server-Side Request Forgery (SSRF)

SSRF shows up as the *server* making connections the browser never would: requests to
link-local metadata IPs, RFC1918 addresses, loopback, or URL parameters containing full URLs
pointing at internal hosts.

## What to log / where it shows up
- **Egress firewall / proxy / VPC flow logs**: the ground truth — the app server initiating outbound connections to `169.254.169.254`, `127.0.0.1`, `10/8`, `172.16/12`, `192.168/16`, or odd ports (6379 Redis, 11211 memcached, 25 SMTP).
- **Web server logs**: URL-fetching parameters (`url=`, `uri=`, `path=`, `callback=`, `webhook=`, `image=`) containing IPs, internal hostnames, or redirect chains.
- **DNS logs**: lookups for `*.burpcollaborator.net`, `*.oast.*`, `*.interactsh.com`, `*.requestbin.*` — near-definitive proof of active OOB testing.
- **Cloud audit logs**: IMDS credential use from an unexpected IP (see `cloud-imds-ssrf`).

## Sigma rule
```yaml
title: SSRF Indicator in Outbound Connection from Application Server
id: f0646158-ecdc-4515-a468-cc43e1958cc8
status: experimental
description: Detects application servers initiating connections to link-local metadata IPs, loopback, or internal address space commonly targeted via SSRF.
logsource:
    category: firewall
detection:
    selection_src:
        SourceIsServer: 'true'    # scope to app/web server subnets in your SIEM mapping
    selection_dst:
        DestinationIp|cidr:
            - '169.254.169.254/32'
            - '169.254.170.2/32'  # ECS task metadata
            - '127.0.0.0/8'
            - '0.0.0.0/32'
            - '10.0.0.0/8'
            - '172.16.0.0/12'
            - '192.168.0.0/16'
    filter_expected:
        DestinationPort:
            - 443
            - 80
        KnownService: 'true'      # map internal service discovery/health checks here
    condition: selection_src and selection_dst and not filter_expected
falsepositives:
    - Health checks, service discovery, and internal API calls from app tiers
    - Container platforms that legitimately query the node metadata service
level: high
tags:
    - attack.t1190
    - attack.t1552.005
    - cwe.918
```

## Behavioral signals
- URL-parameter values cycling through IP-obfuscation forms — decimal (`2130706433`), hex (`0x7f000001`), IPv6 (`[::1]`), `@`-tricks — one source probing filter logic.
- An app request to a public URL that 301-redirects to an internal address (redirect-based filter bypass).
- DNS lookups for known OOB callback domains from the app tier.

## False positives
- Apps that legitimately fetch user-supplied URLs (screenshot services, link unfurlers, webhooks) — baseline the expected destination set and alert on deviation, not existence.
- Load balancer / monitoring health checks — whitelist those source/destination pairs explicitly.
