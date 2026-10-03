# radare2 cheatsheet

## Basic recon

```
rabin2 -I sample.exe     # file info: format, arch, bits, entry point
rabin2 -S sample.exe     # sections
rabin2 -i sample.exe     # imports
rabin2 -E sample.exe     # exports
rabin2 -s sample.exe     # symbols
rabin2 -z sample.exe     # strings
rabin2 -zz sample.exe    # strings, more thorough
```

## Interactive session

```
r2 sample.exe
```

```
aaa          # standard auto-analysis (don't lead with the heavier aaaa)
afl          # list functions
iz           # strings in data sections
iS           # sections
is           # symbols
s entry0     # seek to entry point
pdf          # disassemble current function
VV           # visual graph mode
q            # quit
```

## Strings & cross-references

```
iz~http          # strings matching "http"
iz~error
afl~main         # functions matching "main"
axt <addr>       # who references this address/string
s <addr>         # seek there
pdf              # read the function
```

## Viewing

```
px 64        # hexdump 64 bytes at current seek
pd 20        # disassemble 20 instructions
psz          # read string at current seek
pxa          # friendlier hexdump
```

## Patching (write mode — back up first)

```
r2 -w sample.exe      # or `oo+` inside a session
```

```
s 0x401000
wa nop                # assemble & write
wa jmp 0x401050
wx 9090               # write raw hex bytes
wq                    # write & quit
```

## Non-interactive / batch

```
r2 -A -q -c "afl;iz;ii;q" sample.exe
# -A auto-analyze · -q quiet · -c command string
```

## Companion tools

```
rasm2 -d "9090"                        # disassemble bytes
rasm2 -a x86 -b 64 "xor eax, eax"      # assemble to bytes
radiff2 old.exe new.exe                # diff two binaries
radiff2 -C old.exe new.exe             # code-level diff
rahash2 -a md5 sample.exe              # hashing
rahash2 -a sha256 sample.exe
rax2 0x401000                          # base conversion
rax2 4198400
rax2 -s hello                          # string → hex
```

## Ecosystem (install via r2pm)

```
r2pm -ci r2ghidra      # Ghidra decompiler plugin
r2pm -ci r2dec         # r2dec decompiler
r2pm -l                # list installed plugins

r2xsql -s sample.exe -q "SELECT name, module FROM imports WHERE name LIKE '%Crypt%'"
r2xsql -s sample.exe -q "SELECT addr, content FROM strings WHERE content LIKE '%http%'"

# r2http: stateful HTTP command channel
r2 -N -e http.bind=localhost -e http.port=9393 -e http.sandbox=false -q -c=h sample.exe
curl -sS --data-binary 'aaa'  http://127.0.0.1:9393/cmd
curl -sS --data-binary 'aflj' http://127.0.0.1:9393/cmd

# radius2: symbolic execution
radius2 -p sample.exe -s stdin 96 -X Incorrect
radius2 -p sample.exe -s flag 256 -A . flag -B Correct -X Wrong -j
```
