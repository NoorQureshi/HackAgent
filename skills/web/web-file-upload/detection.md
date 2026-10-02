# Detecting Malicious File Upload

Attackers probe upload endpoints with executable extensions, content-type mismatches, and
polyglot files — then fetch the uploaded file back to execute it. Both halves are loggable.

## What to log / where it shows up
- **Application logs**: upload events with filename, declared content-type, *detected* content-type (magic bytes), size, and storage path.
- **Web server logs**: `POST` to upload endpoints followed shortly by `GET` of the uploaded path — especially `GET /uploads/x.php` returning 200 instead of a download.
- **EDR on the web tier**: the server process spawning shells after the GET hits (webshell execution — see `web-command-injection`).
- **File integrity monitoring**: new executable files (`.php`, `.jsp`, `.aspx`, `.war`) appearing under web-accessible upload directories.

## Sigma rule
```yaml
title: Executable File Uploaded and Served by Web Server
id: 122adb03-eb52-444a-a751-774d9696e83f
status: experimental
description: Detects HTTP GET requests retrieving executable/script files from upload/media directories — the detonation step of a malicious file upload.
logsource:
    category: webserver
detection:
    selection_path:
        cs-uri-stem|contains:
            - '/upload'
            - '/uploads'
            - '/media'
            - '/files'
            - '/attachments'
            - '/images'
            - '/avatars'
    selection_ext:
        cs-uri-stem|endswith:
            - '.php'
            - '.php5'
            - '.phtml'
            - '.phar'
            - '.jsp'
            - '.jspx'
            - '.asp'
            - '.aspx'
            - '.ashx'
            - '.exe'
            - '.dll'
            - '.war'
            - '.cgi'
            - '.pl'
            - '.py'
            - '.sh'
    selection_status:
        sc-status: 200
    condition: selection_path and selection_ext and selection_status
falsepositives:
    - Legacy apps that genuinely serve scripts from mixed content/code directories (restructure instead of tuning forever)
    - Source-download features serving scripts as `text/plain` (check Content-Type, not just 200)
level: critical
tags:
    - attack.t1105
    - attack.t1505.003
    - cwe.434
```

## Behavioral signals
- Upload-probing sequence: same endpoint receiving `.php`, `.php.jpg`, `.phtml`, `.svg`, `.htaccess` in minutes — extension/filter matrix testing.
- Content-type mismatch: declared `image/png` with magic bytes of a script (`<?php`, `<%`, `GIF89a` polyglot prefix) — log both at ingest.
- Upload immediately followed by GET of the file, then requests carrying `cmd=`/`?0=` query strings — webshell invocation.
- A successful upload from an account with no prior history, from a hosting-provider ASN.

## False positives
- Apps that let users download scripts they uploaded (code-sharing features) — alert on *execution* (200 + server processing as code), not download (`Content-Disposition: attachment`).
- Static-site pipelines where build output includes scripts under `/media` — separate upload paths from deploy paths and scope the rule to the former.
