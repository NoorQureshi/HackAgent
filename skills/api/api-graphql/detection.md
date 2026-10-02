# Detecting GraphQL API Abuse

One endpoint, all the action — GraphQL abuse hides in the *body* of POSTs to `/graphql`:
introspection dumps, alias/batch amplification, and BOLA inside query arguments.

## What to log / where it shows up
- **Application logs with parsed GraphQL**: raw POST bodies are the minimum; ideally log the parsed operation — operation name, root fields, alias count, query depth, and resolver-level authz decisions.
- **API gateway logs**: request rate and body size to `/graphql` — aliased batching makes one request do the work of thousands.
- **Error logs**: GraphQL suggestion errors (`Did you mean "adminUsers"?`) from field brute-forcing — clairvoyance-style schema mapping when introspection is off.

## Sigma rule
```yaml
title: GraphQL Introspection or Abusive Query Pattern
id: b2d63c08-24a3-4d6c-81de-9951d527f883
status: experimental
description: Detects introspection queries and amplification patterns (aliasing, batching, deep nesting) in GraphQL request bodies — schema mapping and rate-limit/brute-force bypass.
logsource:
    category: application
    product: api
detection:
    selection_introspection:
        request_body|contains:
            - '__schema'
            - '__type'
            - 'IntrospectionQuery'
            - 'query IntrospectionQuery'
    selection_alias_amplification:
        # Aliased batching: many aliased calls to one root field in a single query
        graphql_alias_count|gt: 20          # requires parsed-query enrichment
    selection_depth:
        graphql_query_depth|gt: 15          # recursive nesting DoS
    filter_playground:
        source_is_internal_dev: 'true'
    condition: 1 of selection_* and not filter_playground
falsepositives:
    - Apollo Client/Relay devtools and schema-codegen running introspection in dev/staging
    - Legitimate complex dashboard queries — baseline depth/alias counts per known operation
level: medium
tags:
    - attack.t1190
    - attack.t1110
    - cwe.200
    - owaspapi.api1
```

## Behavioral signals
- Introspection disabled → a client then generating thousands of suggestion-error responses — field-name brute-forcing to reconstruct the schema.
- A single POST with dozens of aliased mutations (`a1:login(...) a2:login(...)`) — credential brute-force that evades per-request rate limits.
- One token calling mutations or nested relations it never used before, immediately after schema-mapping activity — enumeration → exploitation sequence.
- Query cost far exceeding the norm for that client's historical operations (cost-analysis alerting beats fixed thresholds).

## False positives
- Persisted-query allowlists break naive body matching — if you use them, alert on any *non-allowlisted* query hash instead; it's a far stronger control.
- CI/CD codegen and devtools introspection — restrict introspection to non-prod and the FP disappears entirely.
