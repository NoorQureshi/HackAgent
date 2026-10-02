# Detecting Kerberoasting and AS-REP Roasting

Roasting is loud at the KDC: one account requesting many RC4-encrypted service tickets in
minutes, or AS-REQs without pre-authentication against many usernames. Windows Security logs
catch both.

## What to log / where it shows up
- **DC Security Event 4769** (TGS requested): ticket encryption type `0x17` (RC4) for service accounts is the classic signal — attackers downgrade to RC4 because it's fast to crack.
- **DC Security Event 4768** (TGT requested) with pre-auth type `0` from accounts with "Do not require Kerberos preauthentication" — AS-REP roasting.
- **Directory-service logs**: LDAP queries enumerating `servicePrincipalName=*` right before the ticket storm.

## Sigma rule
```yaml
title: Kerberoasting — RC4 Service Ticket Request Burst
id: 00a12108-8d37-4de3-a7fb-4a4c474d951a
status: experimental
description: Detects a single account requesting multiple RC4-encrypted Kerberos service tickets (TGS) for accounts with SPNs — the offline-crackable downgrade pattern of Kerberoasting.
logsource:
    product: windows
    service: security
detection:
    selection:
        EventID: 4769
        TicketEncryptionType: '0x17'        # RC4-HMAC — crackable; AES (0x11/0x12) is the norm on modern domains
    filter_machine_accounts:
        ServiceName|endswith: '$'           # machine-account SPNs (CIFS/host) are noise; roastable targets are user service accounts
    filter_service_accounts:
        AccountName|endswith: '$'
    condition: selection and not 1 of filter_*
    # Correlate: alert when count(distinct ServiceName) by AccountName > 5 within 10 minutes.
falsepositives:
    - Legacy applications that genuinely still use RC4 — inventory and force AES on their accounts (msDS-SupportedEncryptionTypes)
    - Read-only DC replication and trust flows emitting 4769 for machine accounts (filtered above)
level: high
tags:
    - attack.t1558.003
    - attack.t1558.004
```

## Behavioral signals
- One account requesting TGS for *every* SPN-bearing account in the domain within minutes — GetUserSPNs/nxc `--kerberoasting` enumeration pattern; volume per account is the discriminator.
- SPN enumeration LDAP query (`servicePrincipalName=*`, `adminCount=1`) from a workstation immediately before the ticket burst.
- RC4 requests against accounts that have supported AES for years — downgrade is deliberate; legit RC4 clients hit the same few services repeatedly.
- AS-REP variant: 4768 with `PreAuthType: 0` across a username list, no corresponding logon failures — no creds needed, so no failed-auth noise precedes it.

## False positives
- Real legacy apps on RC4 — the correct fix is enabling AES on those accounts, which also shrinks the attack surface.
- Vulnerability scanners (Tenable/Qualys AD checks) request a few TGSs — they hit a handful of SPNs, not dozens; keep the volume threshold.
