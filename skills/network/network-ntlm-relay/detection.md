# Detecting NTLM Coercion and Relay

Relays have a distinctive shape: a machine account authenticates to a host it has no business
talking to, seconds after an RPC coercion call, often alongside LLMNR/NBT-NS poisoning on the
segment.

## What to log / where it shows up
- **Windows Security 4624 (type 3, NTLM)**: machine-account (`SERVER$`) or admin logons where source and destination are *both* servers with no normal relationship — the relay landing.
- **Sysmon Event 3 / EDR network telemetry**: hosts listening on SMB/HTTP that aren't servers (Responder/ntlmrelayx), and RPC connections to MS-EFSRPC/MS-RPRN named pipes (coercion).
- **Network IDS / switch logs**: LLMNR/NBT-NS/mDNS responses from non-DNS hosts — poisoning in progress.
- **CA IIS logs**: NTLM POSTs to `/certsrv` from server IPs — ESC8 (see `ad-adcs`).

## Sigma rule
```yaml
title: NTLM Authentication from Machine Account to Unrelated Server
id: 1ca5daaa-e872-4714-89cc-1926ebc232f1
status: experimental
description: Detects a machine account performing NTLM network logon to a server it does not normally contact — the landing signature of coerced/relayed NTLM authentication.
logsource:
    product: windows
    service: security
detection:
    selection:
        EventID: 4624
        LogonType: 3
        AuthenticationPackageName: 'NTLM'
        AccountName|endswith: '$'           # machine accounts should rarely NTLM-auth laterally
    filter_known_flows:
        IpAddress|cidr:
            - '10.10.5.0/24'                # known management/backup subnet — replace with yours
    filter_domain_controllers:
        AccountName:
            - 'ANONYMOUS LOGON'
    condition: selection and not 1 of filter_*
    # Correlate: alert when source/dest pair is novel (no traffic baseline between these hosts
    # in 30 days) — baseline comparison lives in the SIEM, not in Sigma.
falsepositives:
    - Backup agents, SCCM, and monitoring platforms authenticating machine accounts broadly — baseline and whitelist those service hosts
    - Cluster/DFS replication between nodes (usually Kerberos — NTLM fallback is itself worth a look)
level: high
tags:
    - attack.t1557.001
    - attack.t1187
```

## Behavioral signals
- Coercion → auth within seconds: an inbound RPC to `\pipe\efsrpc` or `\pipe\spoolss` on a server, immediately followed by that server's machine account authenticating somewhere new.
- A workstation answering LLMNR/NBT-NS queries — no legitimate reason exists; on any managed segment this is Responder until proven otherwise.
- Machine account auth landing on the CA's web enrollment or on LDAP — the ESC8/RBCD escalation targets, not random file shares.
- Relay-tool UAs and ports: NTLM over HTTP to non-IIS ports (8080, 8000) between servers.

## False positives
- Management tooling (SCCM, backup, vuln scanners) legitimately authenticates machine accounts everywhere — build the baseline, whitelist the *service hosts*, alert on novelty.
- The durable fix is also the FP-killer: enforce SMB signing, LDAP signing + channel binding, and EPA on ADCS — the attack class dies and the remaining hits are real.
