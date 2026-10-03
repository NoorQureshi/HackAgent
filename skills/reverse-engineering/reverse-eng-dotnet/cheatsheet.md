# .NET reversing cheatsheet — obfuscators, de4dot, IL patching

Companion to `SKILL.md`. Identify the obfuscator first (`diec target.exe` or
`de4dot --detect target.exe`), then pick the row.

## Obfuscator decision table

| Obfuscator | de4dot `--type` | Tells | Auto-strip | Manual notes |
|---|---|---|---|---|
| ConfuserEx 1.x/2.x | `cfze` | `<module>` anti-tamper, switch-dispatch flattening, string encryption, embedded `.cmp` resources | mostly | new builds need the anti-tamper check patched first |
| ConfuserEx 3.x / custom forks | `cfze` | same + custom protectors | partial | runtime dump / dnlib script |
| SmartAssembly | `sa` | `SmartAssembly.Runtime.*` string encoding, compressed resources, hidden calls | yes | best de4dot compatibility |
| Babel.NET | `babel` | encrypted method bodies, control flow | yes | — |
| Eazfuscator.NET | `eaz` | string/resource encryption, expression obfuscation | partial | feed the string decryptor token manually |
| .NET Reactor | `reactor` | necrobit (method bodies encrypted into resources) + anti-tamper | old versions | 4.x+: dump the running process, rebuild metadata with dnlib |
| Agile.NET / CliSecure | `agile` | encrypted method bodies | yes | — |
| Themida .NET | — | native wrapper + virtualization | no | memory dump, treat as native |

## de4dot usage

```powershell
de4dot target.exe -o target-clean.exe        # auto-detect — enough most of the time
de4dot --detect target.exe                   # report only, no stripping
de4dot --type cfze target.exe -o clean.exe   # force a family when auto-detect fails
de4dot --strtyp delegate --strtok 0x06000012 target.exe -o clean.exe
```

`--strtyp/--strtok` runs only the string decryptor (by method token) and leaves control flow
alone — use when you want plaintext strings without touching anti-tamper. Find the decryptor in
dnSpyEx: a `static string` method called from everywhere with a numeric constant argument; its
token shows in the IL view.

## Anti-tamper / anti-debug bypass

| Technique | Where | Bypass |
|---|---|---|
| ConfuserEx anti-tamper (method-body hash) | `<module>` `.cctor` | IL-edit the check to `ret`, save, then de4dot |
| `Debugger.IsAttached` / `IsLogging` | any method | IL: `ldc.i4.0; ret` |
| Timing checks (`DateTime.Now` deltas) | method entry | nop the comparison |
| `CheckRemoteDebuggerPresent` P/Invoke | — | nop the call |
| Exception-driven control flow (`throw`+`catch` dispatch) | main logic | don't nop — break on the exception type, trace the `catch` switch |

Fallback ladder when de4dot fails: `--detect` and re-pick the family → runtime dump (MegaDumper /
ExtremeDumper / Process Hacker module export) → dnlib script → go dynamic and read plaintext at
the decryptor's return without stripping at all.

## IL patch recipes (dnSpyEx → right-click method → Edit IL)

```text
Force a check true:    ldc.i4.1 / ret                      (method now returns true)
Force false:           ldc.i4.0 / ret
Invert a branch:       swap brfalse.s <-> brtrue.s
Delete a validation:   nop the whole block (keep stack balanced), or ldc.*; ret
Change a constant:     edit the operand of ldc.i4.* / ldstr directly
Async/state machines:  patch inside the generated MoveNext() — the state switch and the
                       per-case bodies. C# Edit Method on async code almost always fails to
                       recompile; IL is the only reliable route.
```

Then File → Save Module → write to a *new* file; keep the clean and original copies for the diff.

## Sharp* red-team tooling quick map

Most Sharp* tools ship unobfuscated (occasional ConfuserEx). Read order:
`Program.Main` / command dispatch (Rubeus: `switch(command)` → one class per subcommand) →
`Interop.*` namespace for the P/Invoke native calls → embedded resources for config/templates:

```powershell
powershell -c "[System.Reflection.Assembly]::LoadFile('target.exe').GetManifestResourceNames()"
```

| Tool | Look at |
|---|---|
| Rubeus | `Ask.TGS` (kerberoast), `Interop.Lsa*` P/Invoke (`LsaCallAuthenticationPackage`) |
| SharpHound | LDAP query construction, collected property set |
| Seatbelt | check list and per-check logic |
| Loaders/stealers | encrypted `byte[]` field + AES/XOR decrypt method → break at its return for C2/keys |

---
_Portions adapted from [reverse-skill](https://github.com/zhaoxuya520/reverse-skill) by zhaoxuya520, MIT License._
