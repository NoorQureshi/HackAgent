# EDR evasion cheatsheet

Companion to `SKILL.md` — hook survey, unhook/syscall techniques, and telemetry blinding.
Authorized red-team use only.

## EDR fingerprint table

| Product | Userland components | Kernel drivers | Primary surveillance |
|---------|--------------------|----------------|---------------------|
| CrowdStrike Falcon | `CSFalconService.exe`, `CSAgent.sys` injected | `CSAgent.sys`, `CSBoot.sys` | Heavy kernel callbacks + ETW-TI; few userland hooks (cloud) |
| MS Defender for Endpoint | `MsMpEng.exe`, `MpClient.dll` | `WdFilter.sys`, `WdBoot.sys`, `WdNisDrv.sys` | Everything: AMSI + ETW-TI + ntdll hooks + kernel callbacks |
| SentinelOne | `SentinelAgent.exe` | `SentinelMonitor.sys` | Heavy ntdll hooks + kernel callbacks + own ETW provider |
| Elastic Defend | `elastic-endpoint.exe` | `elastic-endpoint-driver.sys` | Mostly ETW + light ntdll hooks |
| ESET | `ekrn.exe`, `eamsi.dll` | `eamonm.sys`, `epfwwfp.sys` | Very many userland hooks (NtCreateFile, NtOpenProcess...) |
| Sophos Intercept X | `SophosFileScanner.exe` | `SophosED.sys`, `hmpalert.sys` | ntdll hooks + HMPA memory protection + callbacks |
| Kaspersky | `avp.exe` | `klif.sys`, `klhk.sys` | Heavy userland hooks + own minifilter |
| Carbon Black | `RepMgr.exe`, `RepWAV.exe` | `ParityDriver.sys` | Mostly kernel callbacks + ETW |

Fast fingerprint: match process names (`CSAgent`, `SentinelAgent`, `elastic-endpoint`, `ekrn`,
`MsMpEng`, `SophosFileScanner`, `avp`, `TmListen`) and drivers under
`C:\Windows\System32\drivers\*.sys`.

## ntdll exports an EDR almost always hooks

| Function | Behavior watched | ATT&CK |
|----------|-----------------|--------|
| `NtCreateThreadEx` | remote-thread / APC injection | T1055.002/.004 |
| `NtAllocateVirtualMemory(Ex)` | RWX shellcode allocation | T1055 |
| `NtProtectVirtualMemory` | RW→RX page flips | T1055 |
| `NtWriteVirtualMemory` | cross-process writes | T1055.012 |
| `NtMapViewOfSection` / `NtCreateSection` | section injection (doppelgänging/ghosting) | T1055.013 |
| `NtOpenProcess` | handle to target process | T1057 |
| `NtQueueApcThread(Ex)` | APC injection | T1055.004 |
| `NtCreateUserProcess` etc. | child processes (incl. PPID spoof) | T1106 |
| `NtSetContextThread` / `NtResumeThread` | thread hijack & resume | T1055.003 |
| `NtQuerySystemInformation` | process/driver/handle enum | T1057/T1082 |
| `NtAdjustPrivilegesToken` | SeDebugPrivilege etc. | T1134 |
| `NtLoadDriver` | BYOVD | T1543.003 |

Verify a hook: a clean `Nt*` prologue is `mov r10,rcx; mov eax,<SSN>; ...; syscall; ret`. A first
instruction of `jmp <addr>` = hooked; follow it to find the EDR's trampoline and owning DLL.
Automate: `pe-sieve64.exe /pid <pid> /shellc 3 /modules 3 /imp 3 /data 3 /dir hooks_dump` — the
`*.tag` files list hook addresses/RVAs for IDA. In kernel debug: `dx -r1 nt!PspCreateProcessNotifyRoutine`,
`!object \Callback` enumerate registered callbacks (PChunter/DRVHV from userland).

## Unhook & syscall techniques

- **Perun's Fart / fresh ntdll** — remap the clean on-disk ntdll (`NtCreateSection` SEC_IMAGE →
  `NtMapViewOfSection`) and `memcpy` its `.text` over the hooked one. Catch: `NtProtectVirtualMemory`
  is itself hooked (chicken-and-egg — call it via direct syscall first), and the write fires ETW-TI
  `PROTECTVM` events — patch ETW before unhooking.
- **Direct syscall** — own stub: `mov r10,rcx; mov eax,<SSN>; syscall; ret`. Skips userland hooks,
  but the `syscall` executes from your `.text` — kernel telemetry flags non-ntdll RIP.
- **Indirect syscall** — `jmp` into a legitimate ntdll `syscall;ret` gadget so RIP stays in ntdll:
  `python3 syswhispers.py --preset all --action edit --mode jumper -o syscalls`
  (`--mode jumper_randomized` randomizes the gadget to reduce signatures).
- **SSN resolution** — Hell's Gate reads `mov eax,<SSN>` from each `Nt*` export (fails when hooked);
  Halo's Gate infers a hooked SSN from unhooked neighbours (SSNs increment); Tartarus Gate also
  validates the `syscall;ret` gadget when hooks preserve it.
- **HWBP Blindside** — set DR0–DR3 on hooked function entries + a VEH; on the single-step exception,
  rewrite `ContextRecord->Rip` to a clean ntdll `syscall;ret`. No memory writes, hooks stay in
  place. Per-thread only; `NtSetContextThread` may be hooked.
- **Call-stack spoofing** — EDRs run `RtlCaptureStackBackTrace` at syscall entry; an implant frame
  in non-image-backed memory is a high-confidence alert. CallStackSpoofer swaps in a fake legitimate
  stack for the syscall; SilentMoonwalk uses a desynchronized stack with forged `RUNTIME_FUNCTION`
  unwinding.

Effectiveness snapshot: Perun's Fart — medium (ETW catches it); direct syscall — low-medium;
indirect + Halo's Gate — medium-high; HWBP Blindside and stack spoofing — high. Field-proven combo:
**Halo's Gate + indirect syscall + CallStackSpoofer + ETW patch**.

## Telemetry blinding (ETW / AMSI)

Key ETW providers: Threat-Intelligence (ETW-TI) `{F4E1897C-BB5D-5668-F1D8-040F4D8DD344}`,
AMSI `{A0C1853B-5C40-4B15-8766-3CF1C58F985A}`. Call chain: app → `EtwEventWrite` → `NtTraceEvent`
→ kernel → EDR subscriber session.

- **ETW patch A** — head-patch `ntdll!EtwEventWrite`: bytes `33 C0 C3` (`xor eax,eax; ret`). OPSEC:
  secure an unhooked/indirect-syscall `NtProtectVirtualMemory` path first, or the write alerts
  before the patch lands.
- **ETW patch B** — patch `EtwEventEnabled` to always-false (`32 C0 C3` = `xor al,al; ret`);
  stealthier against byte-integrity checks on `EtwEventWrite`.
- **ETW patch C** — `NtTraceControl` to stop the session; needs high privilege and the stop itself
  is visible. Rarely worth it.
- **AMSI patch** — `amsi.dll!AmsiScanBuffer` head: `B8 57 00 07 80 C3` (`mov eax,0x80070057; ret`,
  E_INVALIDARG). Variants that touch no memory: HWBP on the entry (VEH sets `RAX=0x80070057`, RIP to
  a `ret`), corrupting the `AmsiContext` "AMSI" magic, or reflectively loading a clean amsi.dll copy.

Anti-forensics (T1070): disable ScriptBlock/Module logging & transcription via
`HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\*`; clear PSReadLine history
(`Remove-Item (Get-PSReadLineOption).HistorySavePath`); delete your Prefetch `.pf` files (SYSTEM);
timestomp by copying `CreationTime`/`LastWriteTime` from a system file. Deleting `.evtx` writes an
Event ID 1102 "log cleared" — patch `wevtsvc.dll` in memory instead if you must.

## Sysmon evasion

Watch Event IDs: 1 ProcessCreate, 7 ImageLoad, 8 CreateRemoteThread, 10 ProcessAccess, 11
FileCreate, 12–14 registry, 22 DNS, 25 ProcessTampering. Avoid spawning processes; PPID-spoof with
`UpdateProcThreadAttribute(PROC_THREAD_ATTRIBUTE_PARENT_PROCESS)` to `explorer.exe`; prefer module
stomping over hollowing (ID 25); execute in-process (`NtCreateThreadEx` on self, APC, Early Bird)
instead of remote threads (ID 8); DNS over HTTPS (ID 22).

## OPSEC execution order

```
1. AMSI bypass (HWBP preferred — no amsi.dll writes)
2. ETW patch (EtwEventWrite) — blind telemetry before anything it watches
3. NtProtectVirtualMemory via indirect syscall — safe page-permission channel
4. Unhook ntdll (Perun's Fart) or enable indirect syscalls
5. Call-stack spoof setup
6. Payload (injection / lateral / LSASS)
7. Clean traces (history / Prefetch / timestomp)
```

Wrong order = the EDR gets the alert mid-chain (e.g. unhook first → ETW-TI reports the module
modification immediately).

## References

- SysWhispers3 — github.com/klezVirus/SysWhispers3 · Hell's/Halo's Gate — github.com/am0nsec/HellsGate,
  SafeBreach-Labs/HalosGate-PoC · Tartarus Gate — github.com/trickster0/TartarusGate
- CallStackSpoofer — github.com/WithSecureLabs/CallStackSpoofer · SilentMoonwalk —
  github.com/klezVirus/SilentMoonwalk · Blindside — CyberArk research blog
- Ekko — github.com/Cracked5pider/Ekko · Foliage — github.com/SecIdiot/FOLIAGE
- pe-sieve — github.com/hasherezade/pe-sieve · sysmon-modular (olaf) — github.com/olafhartong/sysmon-modular
- MITRE ATT&CK T1562.001/.002/.006, T1070, T1055 · ired.team defense-evasion notes

---
_Portions adapted from [reverse-skill](https://github.com/zhaoxuya520/reverse-skill) by zhaoxuya520, MIT License._
