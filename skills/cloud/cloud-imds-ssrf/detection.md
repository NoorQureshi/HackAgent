# Detecting IMDS Credential Theft via SSRF

Stolen instance credentials are used from somewhere the instance is not: a role's temporary
keys appearing in API calls from an external IP is the near-perfect signal. The earlier stage —
the metadata fetch itself — shows in egress logs.

## What to log / where it shows up
- **VPC flow / egress logs**: connections from app instances to `169.254.169.254` (EC2/ECS metadata) — every instance uses IMDS, but *which process* and *when* matters; baseline it.
- **CloudTrail / audit logs**: calls made with instance-role credentials where `sourceIPAddress` is outside your VPC/NAT range — credential exfil confirmed.
- **Host logs (auditd/Sysmon)**: which process queried IMDS — a web app process tree doing it is suspicious; the cloud-init/SSM agents doing it is normal.

## Sigma rule
```yaml
title: Cloud Instance Role Credentials Used Outside the Instance
id: 850ec4e9-f139-4aef-a083-3a68325e360a
status: experimental
description: Detects AWS temporary credentials issued to an EC2 instance role being used from an IP address outside the instance — the telltale of IMDS credential theft via SSRF or RCE.
logsource:
    product: aws
    service: cloudtrail
detection:
    selection:
        userIdentity.type: 'AssumedRole'
        userIdentity.principalId|contains: ':i-'    # session issued to an EC2 instance profile
    filter_same_network:
        sourceIpAddress|cidr:
            - '10.0.0.0/8'        # replace with your VPC CIDRs
            - '172.16.0.0/12'
            - '192.168.0.0/16'
    filter_vpc_endpoint:
        sourceIpAddress|startswith: 'vpce-'    # calls via VPC endpoints carry no public IP
    condition: selection and not filter_same_network and not filter_vpc_endpoint
falsepositives:
    - NAT gateway egress — enrich to distinguish VPC NAT IPs from truly external IPs, or alert on non-NAT public IPs
    - Credentials legitimately exported to a CI runner (bad practice, but alive in many orgs)
level: critical
tags:
    - attack.t1552.005
    - attack.t1550
    - cwe.918
```

## Behavioral signals
- IMDS access from a process tree rooted at the web server (nginx→php→curl 169.254.169.254) — SSRF, not normal instance bootstrapping.
- `GetCallerIdentity` as the *first-ever* call for a role's session, from an unknown IP — the attacker's proof-of-access step.
- A role suddenly calling services it never touches (S3 listing from a web-server role, IAM enumeration) — scoping after theft.
- IMDSv1-only usage on instances that should enforce IMDSv2 — audit `HttpTokens: required` coverage fleet-wide; the absence is the pre-condition.

## False positives
- Developers pulling instance creds for local debugging — a policy violation to fix, not an FP to tune away.
- VPN/egress architectures making internal use look external — key the rule on your known egress/NAT IP set, keep it current.
