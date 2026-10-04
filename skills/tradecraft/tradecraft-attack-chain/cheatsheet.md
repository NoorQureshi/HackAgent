# Attack-chain playbooks & decision matrix

Pick the playbook matching your starting position and objective. Each phase routes to the
specialist skills named here and in the parent `SKILL.md`; the decision matrix at the bottom
covers any state that doesn't match a playbook's start.

## Playbook: external web app → domain controller
1. Subdomain enum + port scan (`recon-subdomain-enum`, `recon-arsenal`)
2. Fingerprint → known-vuln components (`recon-techstack-fingerprinting`, nuclei)
3. Exploit to webshell/RCE (`web-*` per class — sqli, ssti, file-upload, deserialization)
4. Internal situational awareness (ipconfig, arp, `net user` — `privesc-enumeration`)
5. Tunnel in (`network-pivoting-tunneling` — chisel/ssh/frp)
6. Internal scan from the foothold
7. Credential theft (mimikatz / secretsdump / config files)
8. Lateral movement (PtH, WMI, WinRM — `ad-pivot-arsenal`)
9. Domain mapping (BloodHound — `tradecraft-attack-path-mapping`)
10. Domain escalation (`ad-kerberoasting`, `ad-adcs`, `ad-delegation-abuse`, DCSync if in RoE)

Chain: subfinder → httpx → nuclei → sqlmap → chisel → nmap → mimikatz → netexec → bloodhound → certipy

## Playbook: phishing → internal network (RoE must include social engineering)
1. Employee/surface OSINT (`recon-osint`, `social-eng-phishing`)
2. Pretext + payload per `social-eng-methodology` (macro doc, LNK, ISO, HTML smuggling)
3. Deliver via the authorized platform; wait for callback
4. Local enum + privesc (`privesc-enumeration`, `privesc-windows-tokens`)
5. Credential extraction → lateral movement → objective as above
6. Persistence only if explicitly authorized, with an agreed removal date

Chain: theHarvester → gophish → CS/Sliver → mimikatz → bloodhound

## Playbook: proximity/physical → internal network
1. Site survey per `social-eng-physical` (Wi-Fi footprint, badge type, USB exposure)
2. Wi-Fi attack (`wireless-wpa2-attacks`, `wireless-evil-twin`) or an authorized USB drop /
   drop-box implant per RoE
3. Internal foothold → continue from step 5 of the web→DC playbook

## Playbook: cloud environment
1. Cloud asset discovery (`recon-cloud-assets`)
2. Storage enumeration (`cloud-s3-exposure`)
3. SSRF → instance metadata (`web-ssrf` → `cloud-imds-ssrf`) for temporary credentials
4. Cloud API enumeration (IAM, compute, functions, databases)
5. Privilege escalation (`cloud-iam-privesc` — PassRole/AssumeRole paths)
6. Lateral: cross-account / cross-region
7. Objective: prove data access with minimal reads

Chain: subfinder → nuclei → aws-cli → pacu/ScoutSuite

## Playbook: AD CS
1. `certipy find` — enumerate templates and CAs
2. Identify a misconfiguration (ESC1–ESC8 — `ad-adcs`)
3. Request a certificate as the target identity
4. Authenticate with it → NTLM hash or TGT
5. DCSync for the full credential dump (only if in RoE)

## Decision matrix — state → next priority
| You hold | Next |
|---|---|
| Only a domain | Subdomain enum → port scan → fingerprint |
| A web vuln | Shell → internal situational awareness |
| Low-priv shell | Privesc → credential theft |
| One internal host | Tunnel → internal scan → lateral |
| Domain user creds | BloodHound → shortest path (`ad-*`) |
| Domain admin hash | DCSync → objective (golden ticket only if authorized) |
| Cloud keys (AK/SK) | Enum permissions → `cloud-iam-privesc` → data |
| Phishing callback | Local privesc → creds → lateral |
| Physical/proximity access | Internal scan → as above |

## Evasion notes (EDR present)
Full product fingerprinting and hook-table analysis: `reverse-eng-edr-analysis`. In brief:
- **Static signatures** → custom builds, encrypted payloads; never run public tooling unmodified.
- **Userland hooks (ntdll)** → direct syscalls / unhooking.
- **Memory scans** → sleep-encrypt, module stomping; prefer fileless execution.
- **Network** → blend into normal HTTPS; legit-service channels over exotic protocols.
- **Logs** → know what each action writes before you act; LOLBins (certutil, mshta, rundll32,
  regsvr32, wmic, msiexec, bitsadmin) introduce less new surface than dropped tools.

OpSec floor: least action, off-hours timing where agreed, identify honeypots before using
found credentials, spread noisy steps across time windows.

---
_Portions adapted from [reverse-skill](https://github.com/zhaoxuya520/reverse-skill) by zhaoxuya520, MIT License._
