# Detecting Server-Side Template Injection (SSTI)

SSTI shows up as template expressions — `{{7*7}}`, `${7*7}`, `<%= 7*7 %>` — in user input,
followed by rendered output containing `49` (or worse: process execution artifacts on the
server).

## What to log / where it shows up
- **Web server logs**: GET/POST parameters containing template syntax (`{{`, `${`, `<%=`, `#{`, `{%`).
- **Application logs**: template-engine stack traces (Jinja2 `UndefinedError`, Freemarker `freemarker.core.*`, Thymeleaf `TemplateProcessingException`) triggered by user input.
- **EDR on the web tier**: the web/app server process spawning shells or running `id`/`whoami`/`curl` — SSTI exploitation reaching RCE.
- **Outbound connections from the app server** to OOB callback domains during probing.

## Sigma rule
```yaml
title: Server-Side Template Injection Payload in Web Request
id: 3deb48fb-435a-48b6-920f-d35db737fe84
status: experimental
description: Detects template-engine expression payloads commonly used to probe and exploit SSTI in HTTP parameters.
logsource:
    category: webserver
detection:
    selection:
        cs-uri-query|contains:
            - '{{'
            - '${'
            - '<%='
            - '#{'
            - '{%'
            - '7*7'
            - '__class__'
            - '__mro__'
            - '__subclasses__'
            - 'freemarker'
            - 'Runtime.getRuntime'
            - 'T(java.lang.Runtime)'
    filter_static:
        cs-uri-stem|endswith:
            - '.js'
            - '.map'    # front-end bundles legitimately contain these tokens
    condition: selection and not filter_static
falsepositives:
    - Angular/Vue front-ends whose templates legitimately carry `{{ }}` — check whether the token reaches the *server* as input
    - Support forms where users paste code snippets
level: high
tags:
    - attack.t1190
    - attack.t1059
    - cwe.1336
```

## Behavioral signals
- Polyglot probing: one session cycling `{{7*7}}` → `${7*7}` → `<%= 7*7 %>` → `#{7*7}` — the attacker fingerprinting the engine.
- Escalation sequence after a `49` renders: payloads growing from math to `__class__.__mro__` traversal to command execution.
- EDR on the app host: the JVM/Python/Ruby server process spawning `/bin/sh` or `cmd.exe` — RCE confirmed regardless of what the web logs show.

## False positives
- Rich-text fields, code-paste boxes, and template-editing admin UIs — scope the rule to params that are *rendered*, not stored verbatim.
- Front-end frameworks shipping `{{ }}` in static assets — the `filter_static` block above handles the common cases; verify with your routes.
