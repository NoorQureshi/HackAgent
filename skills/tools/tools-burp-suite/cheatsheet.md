# Burp MCP tool inventory & scenario workflows

Companion to `SKILL.md`. Tool names below follow the community full-coverage Burp MCP extensions
(~78 tools, HTTP API on `127.0.0.1:9876`, stdio bridge for MCP clients). PortSwigger's official
"MCP Server" BApp exposes a ~20-tool subset with different names — list yours with
`GET http://127.0.0.1:9876/tools` and adapt.

## Tool inventory by module

### Proxy history
| Tool | Key params | Purpose |
|------|-----------|---------|
| `proxy_history` | limit, offset, url_filter, method_filter, status_filter | List captured requests |
| `proxy_detail` | index | Full request/response for one entry |
| `proxy_websocket` | limit | WebSocket message history |
| `proxy_history_filtered` | has_notes, color, limit | Filter by annotation/highlight |
| `proxy_clear` | — | Clear history |

### HTTP / Repeater
| Tool | Key params | Purpose |
|------|-----------|---------|
| `send_request` | method, url, body, headers | Fire a request through Burp |
| `repeater_send` | request, host, port, https | Send, return response |
| `repeater_modify_send` | request, replace_header, add_header, replace_body | Mutate then replay |
| `send_to_repeater` | request, tab_name | Stage for manual work |

### Intruder
| Tool | Key params | Purpose |
|------|-----------|---------|
| `send_to_intruder` | request | Stage a request |
| `intruder_attack` | url_template, from, to, pad_digits, success_length_not | Numeric range enum (sync) |
| `intruder_attack_async` | same + threads | Multi-threaded enum |
| `intruder_attack_wordlist` | url_template, wordlist | Dictionary attack |
| `intruder_pitchfork` | url_template, placeholders | Multi-param parallel |
| `intruder_cluster_bomb` | url_template, placeholders, max_requests | Cartesian product |
| `intruder_battering_ram` | url_template, wordlist, placeholder | Same payload everywhere |
| `intruder_with_options` | + throttle_ms, payload_encoding, grep_extract, record_time | Advanced options (timing → blind detection) |

### Scanner / crawl / scope
| Tool | Key params | Purpose |
|------|-----------|---------|
| `scan` / `scan_active` | url / request, host, port | Guided scan / active scan one request |
| `scan_results` | limit | Issue list |
| `scan_issue_detail` | index | Issue detail |
| `crawl` | url | Spider the target |
| `get_scope` / `add_to_scope` / `remove_from_scope` | url | Scope management |

### Collaborator (OOB)
| Tool | Key params | Purpose |
|------|-----------|---------|
| `collaborator_generate` | count | Mint OOB payload URLs |
| `collaborator_poll` | — | Poll for interactions |

### Encode / transform / PoC
| Tool | Key params | Purpose |
|------|-----------|---------|
| `encode` / `decode` | input, type (base64/url/hex) | Transforms |
| `payload_process` | input, operation | md5/sha*/reverse etc. |
| `convert_request` | request, convert_to | Change method/content-type |
| `export_request` | request, host, format (curl/python) | Export as code |
| `generate_csrf_poc` | request, host | CSRF PoC HTML |
| `extract_from_response` | index, regex | Pull values out of responses |

### Search / annotate / config / analysis
| Tool | Key params | Purpose |
|------|-----------|---------|
| `search_history` | regex, search_in (url/request/response), limit | Regex over history |
| `highlight` / `annotate` | index, color / note | Mark entries |
| `compare` | index1, index2 | Diff two responses |
| `register_http_handler` / `remove_http_handler` | header or match/replace | Auto-modify all traffic |
| `set_upstream_proxy` | proxy_host, proxy_port, type | Proxy chaining / IP rotation |
| `set_dns_override` | hostname, ip | DNS pinning |
| `cookie_jar` | limit, domain | Cookie inventory |
| `token_analysis` / `sequencer` | tokens[] | Entropy / randomness analysis |
| `target_info` | url | Tech-stack fingerprint |
| `add_issue` | name, url, detail, severity | Manually log an issue |

## Scenario workflows

**Full-history triage:** browse target through proxy → `proxy_history` → `proxy_detail` on
candidates → `search_history` for secrets (`Bearer`, `api_key`, JWT `eyJ`) → send suspicious
requests to Repeater → classify findings by OWASP category.

**IDOR sweep:** filter history for `/api/user/<id>`-shaped requests → `repeater_modify_send` with
id+1 / id-1 / 0 / 99999 → `compare` responses → another user's data = confirmed (`web-idor`).

**JWT audit:** `search_history` for `Authorization: Bearer` → `decode` header/payload →
`token_analysis` for entropy → test alg:none / weak-secret / RS256→HS256 confusion (`web-auth-jwt`).

**API endpoint discovery (black-box SPA):** browse the whole app → `proxy_history` →
`search_history` regex `"/api/"` → per endpoint: strip auth (unauth access), swap method
(GET→PUT/DELETE), inject `role=admin`-style fields (`api-mass-assignment`).

**SSRF via Collaborator:** `collaborator_generate` (5 payloads) → find requests with
`url=`/`redirect=`/`callback=`/`webhook=` → `repeater_modify_send` to swap in payloads → wait ~10s →
`collaborator_poll`; any interaction = confirmed (`web-ssrf`).

**Blind SQLi timing:** `intruder_attack_wordlist` with `["'", "' OR '1'='1", "1 UNION SELECT NULL--", "' AND SLEEP(5)--"]`
→ `intruder_with_options` with `record_time=true` → responses >5s flagged as time-blind candidates
(`web-sqli`).

**XSS reflection check:** wordlist `["<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "{{7*7}}"]`
through Intruder → `extract_from_response` for verbatim reflection → re-visit page to distinguish
stored vs reflected (`web-xss`).

**Auth/403 bypass matrix on admin endpoints:** strip Cookie/Token → swap in low-priv token →
`X-Forwarded-For: 127.0.0.1` → `X-Original-URL` / `X-Rewrite-URL` → method swap → path case
(`/Admin`→`/admin`→`/ADMIN`) → `..;/` / `%2e%2e/` variants; anything non-403 is a lead.

**Upload bypass:** find `multipart/form-data` requests → replay with `test.php` / `.jsp` / `.aspx`,
`Content-Type: image/png`, double extension `test.php.jpg`, null byte `test.php%00.jpg` →
`send_request` to the returned path to confirm execution (`web-file-upload`).

**OTP brute-force:** `intruder_attack_async` on the verify endpoint, `from: 0, to: 999999,
pad_digits: 6`, threads 50, success = response length ≠ failure length. No rate limit after
thousands of tries is itself the finding (`web-rate-limit-bypass`).

**CORS misconfiguration:** replay an authenticated API request with `Origin: https://evil.com` →
`extract_from_response` on `Access-Control-Allow-Origin` — reflected origin or `*` with credentials
= exploitable (`web-cors`); `generate_csrf_poc` for the CSRF PoC.

**Signed/encrypted front-ends:** reverse the signature scheme (`web-client-side-signing-bypass`,
`reverse-eng-js`) → `register_http_handler` with the re-sign/decrypt rule → Intruder/Repeater now
operate on plaintext.

---
_Portions adapted from [reverse-skill](https://github.com/zhaoxuya520/reverse-skill) by zhaoxuya520, MIT License._
