# Detecting ADCS Abuse (ESC1–ESC8)

ADCS attacks funnel through the CA: a low-priv user requesting a certificate with a
foreign UPN/SAN, template ACLs changing, or relayed NTLM hitting the web enrollment endpoint.
The CA's own logs see it all.

## What to log / where it shows up
- **CA Security events 4886/4887** (certificate requested / issued): the requester vs the requested subject/UPN — ESC1 is a mismatch between them.
- **CA Security event 4899/4900** (template loaded / CA security settings changed) and **Audit Directory Service Changes** on `pKIEnrollmentService` / template objects — ESC4 prep.
- **IIS logs on the CA** (`/certsrv/certfnsh.asp`): NTLM-authenticated POSTs from server IPs — ESC8 relay (see `network-ntlm-relay`).
- **KDC 4768**: PKINIT TGT requests — a freshly-minted cert authenticating as a privileged user.

## Sigma rule
```yaml
title: Certificate Issued with Requester-Provided Subject Alternative Name
id: 9c4efcd9-c01e-463a-80e8-ddceec992ece
status: experimental
description: Detects certificate requests where the SAN/UPN names a different principal than the requester — the ESC1 pattern (enrollee-supplied subject) and the core of most ADCS escalation paths.
logsource:
    product: windows
    service: security
detection:
    selection:
        EventID: 4887                        # Certificate Services approved/issued a certificate
        san_present: 'true'                  # request carries a subjectAltName
        san_upn_equals_requester_upn: 'false'  # enrich: compare SAN UPN to requesting account
    filter_enrollment_agents:
        requester_is_enrollment_agent: 'true'  # legit agents request on behalf of others
    condition: selection and not filter_enrollment_agents
falsepositives:
    - Enrollment agents (SCEP/NDES, Intune, MDM) requesting certs on behalf of devices — whitelist agent accounts
    - Templates designed for multi-SAN web certs — key on *UPN-type* SANs, not DNS SANs
level: critical
tags:
    - attack.t1649
    - attack.t1078
```

## Behavioral signals
- Certipy-style enumeration: LDAP queries for `pKIEnrollmentService` and template objects from a workstation, followed within minutes by a request to a flagged template.
- ESC4 prep: template object modifications (`msPKI-Certificate-Name-Flag` flipped to enrollee-supplied) shortly before a SAN-mismatched request.
- ESC8 chain: NTLM auth to `/certsrv` from a *server* IP (the relayed machine account), then a PKINIT TGT for a DC account — relay → cert → DCSync, often under an hour.
- A certificate issued to a low-priv account authenticating as `Administrator`/a DC — check 4887 requester against the 4768 that follows.

## False positives
- MDM/NDES enrollment agents — whitelist the exact agent service accounts, never the template.
- Enable 4886/4887 auditing first: without "Audit Certification Services" + template change auditing, these events don't exist and the rule is blind.
