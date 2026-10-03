# Patch diff cheat sheet — tools, patch acquisition, root-cause patterns

Companion to `SKILL.md` (which teaches the 5-step method). Open this for exact commands.
All N-day testing stays inside `scope.txt`.

## 1. Diff tools — install, commands, how to read output

### ghidriff (no IDA needed; recommended default)

```bash
pip install ghidriff                      # downloads Ghidra on first run; or:
export GHIDRA_INSTALL_DIR=/opt/ghidra_11.0

ghidriff old.so new.so                    # minimal
ghidriff old.exe new.exe -o ./diff_out/ --engine VersionTrackingDiff --threaded \
         --max-section-funcs-analyze 5000
ghidriff --list-engines                   # VersionTrackingDiff (default), SimpleDiff, ...

# Big binaries (ntoskrnl): cap per-section analysis to avoid OOM
ghidriff ntoskrnl_old.exe ntoskrnl_new.exe -o /tmp/nt_diff/ \
         --max-section-funcs-analyze 8000 --max-section-funcs-full 800 --threaded

# JSON output for scripted triage / LLM summarization
ghidriff old new -o out/ --json-format
```

Outputs a Markdown report (added/deleted/modified functions + pseudocode diffs), JSON, and a
reopenable Ghidra project. Read `## Summary` (match rate) → `## Strings Diff` (info-leak CVEs
often change strings) → `## Functions → ### Modified` (the money section).

### BinDiff (needs IDA Pro / Ghidra / Binary Ninja)

```bash
# Linux
wget https://github.com/google/bindiff/releases/latest/download/bindiff_8-amd64.deb
sudo dpkg -i bindiff_8-amd64.deb
# Windows: .msi from the releases page, auto-registers as IDA plugin

bindiff --primary=old.BinExport --secondary=new.BinExport --output_dir=./bindiff_out/
```

In IDA: analyze each binary → `File → Produce file → BinExport` → `Edit → Plugins → BinDiff`.
Reading the result: similarity 1.0 = skip; 0.0/unmatched = new or refactored (usually new
features); **0.5–0.95 = the bug fixes**; 0.95–0.99 = mitigation/cleanup. Graph-view block
colors: grey identical, yellow instruction-level diffs, red added/removed, **blue = exists only
in patched — look here first**.

### Diaphora (IDA plugin)

```bash
git clone https://github.com/joxeankoret/diaphora.git   # into IDA plugins dir
# IDA: File → Script file → diaphora.py → "Export current database" (old.sqlite),
# then on the patched binary → "Diff against another database"
```

Tabs: Best matches (skip) · **Partial matches (read these)** · Unreliable (false-positive
prone) · Unmatched. Data lives in SQLite:

```sql
SELECT f1.name, f2.name, ratio FROM results
 WHERE ratio BETWEEN 0.5 AND 0.9 ORDER BY ratio DESC;
```

### radiff2 (radare2; small files / r2 workflows)

```bash
radiff2 -A -C old.bin new.bin        # analyze + function-level diff
radiff2 -j -A -C old new > diff.json # JSON
radiff2 -g main old new | dot -Tpng -o diff.png   # graph of one function
```

### Triage order for the diff report

1. Overall matched ratio < 90% → alignment failure; recheck toolchain/arch/pairing.
2. Rank modified functions: name contains Ioctl/Dispatch/Probe/Copy/Length (+5) · in a known
   attack-surface driver — afd/clfs/win32k (+5) · diff touches a bounds `if`, lock, refcount
   (+3) · strings/logging only (−3).
3. Hand the top ~10 before/after pseudocode pairs to manual review or an LLM root-cause pass.

## 2. Getting patched vs unpatched binaries

### Windows / Patch Tuesday

Info sources: MSRC Security Update Guide + CVRF API · Microsoft Update Catalog ·
Tenable/Rapid7 Patch Tuesday dashboards ("exploited in the wild" first) · ZDI advisories
(usually better root-cause hints than MSRC).

```powershell
# Pull one month's CVE list
$year='2026'; $mon='May'
Invoke-RestMethod "https://api.msrc.microsoft.com/cvrf/v3.0/cvrf/$year-$mon" |
  ConvertTo-Json -Depth 10 | Out-File "msrc-$year-$mon.json" -Encoding utf8

# Unpack an MSU (cab-in-cab)
expand.exe Windows-KB5052000-x64.msu -F:* C:\patches\out\
expand.exe C:\patches\out\Windows-KB5052000-x64.cab -F:* C:\patches\out\
# target binaries land under amd64_microsoft-windows-{component}_*\

# Alternative: apply to an offline WIM for clean patched files
dism /mount-image /imagefile:install.wim /index:1 /mountdir:C:\mnt
dism /image:C:\mnt /add-package /packagepath:Windows-KB5052000-x64.msu
dism /unmount-image /mountdir:C:\mnt /commit

# Symbols from the Microsoft symbol server
symchk /v /r C:\patches\patched\ntoskrnl.exe /s SRV*C:\sym*https://msdl.microsoft.com/download/symbols

# MSP (Office etc.)
msiexec /a base.msi /p update.msp TARGETDIR=C:\patches\office_patched
lessmsi x update.msp C:\patches\office_msp\      # cleaner, no registry writes
```

Prefer **cumulative** MSUs — Express/Delta packages contain only diffs and are hostile to
this workflow. Filter the month's CVEs by: CVSS ≥ 7.0 · exploitation detected/more likely ·
component below · EoP > RCE > info disclosure (EoP weaponizes cheapest).

High-value Windows binaries:

| File | Path | Why |
|---|---|---|
| ntoskrnl.exe | System32\ | object mgmt, `Ob*`/`Ps*`/`Mm*`/`Io*` |
| win32k.sys / win32kfull.sys / win32kbase.sys | System32\ | GUI subsystem, UAF/type-confusion history |
| afd.sys | System32\drivers\ | WinSock AFD, LPE frequent |
| clfs.sys | System32\drivers\ | Common Log FS, repeatedly exploited in the wild |
| cldflt.sys | System32\drivers\ | Cloud Files mini-filter |
| spoolsv.exe / win32spl.dll | System32\ | Print Spooler |
| lsass.exe, ntdll.dll, ksecdd.sys | System32\ | auth, syscall stubs, kernel security |
| rdpcorets.dll / rdpbase.dll | System32\ | RDP |

### Linux

Sources: Ubuntu USN, Red Hat RHSA, Debian DSA, cve.kernel.org.

```bash
# Debian/Ubuntu
apt download linux-image-5.15.0-101-generic        # patched
apt download linux-image-5.15.0-100-generic        # unpatched
apt download linux-image-unsigned-5.15.0-101-generic-dbgsym
dpkg-deb -x linux-image-5.15.0-101-generic_*.deb ./patched/

# RHEL-likes
dnf download --downloadonly --downloaddir=./patched kernel-5.14.0-362.18.1.el9_3
rpm2cpio kernel-5.14.0-362.18.1.el9_3.x86_64.rpm | cpio -idmv -D ./patched/

# vmlinuz → ELF
wget https://raw.githubusercontent.com/torvalds/linux/master/scripts/extract-vmlinux
chmod +x extract-vmlinux
./extract-vmlinux ./patched/boot/vmlinuz-5.15.0-101-generic > vmlinux_5.15.0-101
```

Hot subsystems: `io_uring` (recent-years bug leader) · `net/` (`__skb_*`, `tcp_*`, `nf_*`) ·
`netfilter` (`nft_*`) · `net/sched` · `fs/` (`do_*`, `vfs_*`) · `bpf/` verifier.
LTS-backport play: diff mainline-fixed vs an LTS pair, then check whether a slower branch
(OEM/cloud kernels) backported the same fix — if not, it's still hittable there.

## 3. Patch pattern → root cause → PoC shape

**Integer overflow.** Added: `if (a + b < a)`, `if (a > UINT_MAX - b)`,
`__builtin_add_overflow`, `if (a != 0 && b > UINT_MAX / a)`. Check whether `a`/`b` come from
user input and feed an allocation (`kmalloc(a+b)` / `RtlAllocateHeap`) — overflow → small
alloc → large `memcpy` → heap OOB write. PoC: `a=0xFFFFFFF0, b=0x100` (32-bit) or
`a=0xFFFFFFFFFFFFFFF0, b=0x100` (64-bit).

**OOB read/write.** Added: `if (idx >= ARRAY_SIZE)`, `if (offset + len > buf_size)`,
`if (InputBufferLength < sizeof(STRUCT))`. See which later operation the new `if` guards
(`memcpy`/array index); the old build takes oversized length/index. PoC: set length past the
buffer, index to `array_size + N`, or tune IOCTL `InputBufferLength` to pass the old check and
hit the new one.

**Race / TOCTOU.** Added: `KeAcquireSpinLock*`, `mutex_lock`, `InterlockedIncrement`,
`ObReferenceObject`. Locking says the object was mutated concurrently; a new ref says it was
freed in use. Find two syscall paths over one object where one frees/modifies and the other
uses. PoC hammer:

```c
DWORD WINAPI thread_close(LPVOID h) { while (running) CloseHandle((HANDLE)h); return 0; }
DWORD WINAPI thread_use  (LPVOID h) { while (running) DeviceIoControl((HANDLE)h, IOCTL_X, ...); return 0; }
// several of each, pin threads to cores (SetThreadAffinityMask), run ~30s, wait for the crash
```

**Uninitialized-memory info leak.** Added: `RtlZeroMemory`, `memset(buf,0,...)`,
`output.reserved = 0`. The old build copied kernel stack/heap padding to userland — a KASLR
bypass. PoC: call the IOCTL repeatedly, scan each 8-byte chunk for kernel-address-shaped
values (Windows `0xFFFF...`, Linux `0xFFFFFFFF8...`), find the stable one, derive kbase.

**UAF / refcount.** Added: `if (InterlockedDecrement(&ref) == 0) Free(obj)` or a missing
`ObReferenceObject` on one path. An old error path frees an object the caller still uses.
PoC: spray → trigger the free → reclaim the hole with controlled data → use:

```c
HANDLE objs[1000];
for (int i = 0; i < 1000; i++) objs[i] = CreateObject(...);
trigger_free(objs[500]);
spray_kernel_pool(0xDEADBEEFDEADBEEF, target_sz);   // reclaim
use_after_free(objs[500]);                          // controlled data executes
```

Windows spray: `NtAllocateReserveObject`, pipe attributes, window-class names.
Linux spray: `msgsnd`, `setxattr`, `userfaultfd`-stalled vmas.

**Unvalidated user pointer.** Added: `ProbeForRead`/`ProbeForWrite` + `__try/__except`
(Windows), `access_ok` + `copy_from_user` (Linux). Old build derefs user pointers raw — pass a
kernel address as the "user" buffer for arbitrary read/write.

**Missing access check.** Added: `SeAccessCheck`, capability checks. Old path reachable by
unprivileged callers — just call it as a low-priv user.

## 4. Practice targets (public analyses to calibrate against)

| CVE | Component | Class | Why |
|---|---|---|---|
| CVE-2023-28252 | CLFS | OOB write → LPE | exploited in the wild, public PoC |
| CVE-2022-37969 | CLFS | type confusion → LPE | full public analysis |
| CVE-2021-40449 | Win32k | UAF → LPE | complete write-up |
| CVE-2022-21882 | Win32k | type confusion | born from an *incomplete* fix of CVE-2021-1732 — the classic "one bug, two harvests" |

Method: pick one, run the whole pipeline yourself, then compare your root cause with the
public write-up.
