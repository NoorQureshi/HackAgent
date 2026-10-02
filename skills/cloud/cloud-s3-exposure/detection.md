# Detecting S3 Bucket Exposure and Enumeration

S3 attacks are quiet: anonymous `ListBucket`/`GetObject` calls, bucket-name guessing from
external IPs, and policy changes that open a bucket to the world. CloudTrail data events are
where it all lives.

## What to log / where it shows up
- **CloudTrail management events**: `PutBucketPolicy`, `PutBucketAcl`, `PutPublicAccessBlock` (disabling!), `DeletePublicAccessBlock` — the exposure *being created*.
- **S3 server access logs / CloudTrail data events** (`GetObject`, `ListObjectsV2`): anonymous or cross-account reads — the exposure *being exploited*.
- **DNS/proxy**: bucket-name brute-forcing via S3 endpoints (`<name>.s3.amazonaws.com`) from one source trying hundreds of names.

## Sigma rule
```yaml
title: S3 Bucket Made Public or Accessed Anonymously
id: 3633d2e5-e86e-48dd-a161-1b48f2f299dc
status: experimental
description: Detects S3 policy/ACL changes granting public access, removal of Public Access Block, and anonymous reads of bucket contents.
logsource:
    product: aws
    service: cloudtrail
detection:
    selection_policy_change:
        eventName:
            - 'PutBucketAcl'
            - 'PutBucketPolicy'
        requestParameters|contains:
            - 'AllUsers'
            - 'AuthenticatedUsers'
            - '"Principal":"*"'
            - '"Principal": "*"'
    selection_pab_deleted:
        # Removing the guardrail entirely — the step before a public ACL/policy lands
        eventName: 'DeletePublicAccessBlock'
    selection_pab_disabled:
        eventName: 'PutPublicAccessBlock'
        requestParameters|contains:
            - '"BlockPublicAcls":false'
            - '"BlockPublicPolicy":false'
            - '"IgnorePublicAcls":false'
            - '"RestrictPublicBuckets":false'
    selection_anon_read:
        eventName:
            - 'GetObject'
            - 'ListObjects'
            - 'ListObjectsV2'
        userIdentity.type: 'AnonymousUser'
    condition: 1 of selection_*
falsepositives:
    - Intentionally public buckets (static sites, public datasets) — maintain an allowlist of bucket names and alert on any *new* public bucket
    - CloudFront/OAI distribution reads (not anonymous — they carry a service identity)
level: high
tags:
    - attack.t1530
    - attack.t1552
    - cwe.284
```

## Behavioral signals
- Bucket-name enumeration: one source resolving or requesting hundreds of candidate names (`corp-backup`, `corp-logs`, `corp-dev`) — 404/403 volume on S3 endpoints.
- Anonymous `ListObjectsV2` followed by bulk `GetObject` on the enumerated keys — discovery → exfil, minutes apart.
- `DeletePublicAccessBlock` immediately preceding `PutBucketAcl` — deliberate public exposure; even in an authorized change, this pair deserves review.
- Reads of backup/dump-named objects (`backup.sql`, `dump.gz`, `.env`, `config.json`) from an identity that never touched the bucket before.

## False positives
- Legitimate public content buckets — allowlist by bucket name, and require a ticket/change reference for new entries.
- Vulnerability scanners and bounty researchers probing `*.s3.amazonaws.com` — they will trip the enumeration signal; tune by volume threshold, not silence.
