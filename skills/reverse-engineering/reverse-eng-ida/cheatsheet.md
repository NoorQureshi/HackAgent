# IDA Pro MCP — tool cheatsheet

ida-pro-mcp 2.x tools, grouped by task. Tool names are prefixed by your MCP server name (e.g.
`idapro_decompile`); ~66 tools depending on version, including `py_eval`. Counts and names drift
between releases — list the live tools instead of assuming.

## Session & overview

```
idb_open / idb_list / idb_save          # session management; open returns session_id (database=)
survey_binary(detail_level="minimal")   # arch, entry, funcs, strings, segments, categorized imports
list_funcs(queries=[{"filter": "crypt", "offset": 0, "limit": 20}])
list_globals(queries)
entity_query(kind="imports", filter="Create")   # kinds: functions/globals/imports/strings/names
server_health() / server_warmup()       # warmup pre-loads string cache, Hex-Rays
```

## Decompile & disassembly

```
decompile(addr="main")                            # name or "0x140001000"
disasm(addr="main", max_instructions=100)
analyze_function(addr="main", include_asm=false)  # pseudocode + strings + consts + callers/callees + blocks
func_profile(queries=["main", "sub_401000"])      # size, block count, xref count
```

## Cross-references & data flow

```
xrefs_to(addrs=["sub_401000", "0x404000"])        # who uses this function/string
xref_query(addr="0x401000", direction="to")       # "to" = who references me, "from" = what I reference
callees(addrs=["main"])
callgraph(roots=["main"], max_depth=3)
trace_data_flow(addr="0x401050", direction="backward", max_depth=5)   # or "forward"
```

## Search

```
find_regex(pattern="https?://", limit=20)         # string search by regex
find_regex(pattern="key|password|secret|token", limit=20)
search_text(pattern="call    sub_")               # search the disassembly listing
find_bytes(patterns=["48 89 ?? 24 ??"], limit=10) # byte patterns, ?? wildcard
find(type="immediate", targets=["0xDEADBEEF"])    # or type="string"
```

## Reading data

```
get_bytes(addrs=[{"addr": "0x401000", "size": 64}])
get_string(addrs=["0x404000"])
get_int(queries=[{"addr": "0x405000", "size": 4}])
get_global_value(queries=["g_flag"])
read_struct(queries=[{"addr": "0x405000", "type": "HEADER"}])
search_structs(filter="FILE")
```

## Annotation & patching

```
set_comments(items=[{"addr": "0x401000", "comment": "XOR decrypt loop"}])
append_comments(items=[...])                      # non-destructive
rename(batch={"func":   [{"addr": "sub_401000", "name": "decrypt_payload"}],
              "global": [{"addr": "0x405000", "name": "g_encryption_key"}],
              "local":  [{"func": "decrypt_payload", "old": "v1", "name": "plaintext_buf"}]})
patch_asm(items=[{"addr": "0x401050", "asm": "nop"}])          # or "jmp 0x401080"
patch(patches=[{"addr": "0x401050", "bytes": "9090909090"}])
define_func / undefine / define_code              # fix missed code
```

## Types & stack frames

```
declare_type(decls=[{"name": "PacketHeader",
  "decl": "struct PacketHeader { uint32_t magic; uint16_t type; uint16_t length; uint8_t data[0]; };"}])
set_type(edits=[{"addr": "sub_401000",
  "type": "int __fastcall decrypt(void *buf, int size, const char *key)"}])
infer_types(addrs=["sub_401000"])
type_query / type_inspect
stack_frame(addrs=["main"])
declare_stack(items=[{"func": "sub_401000", "offset": -0x20, "name": "local_buf", "type": "char [32]"}])
```

## Signatures, export, misc

```
make_signature(addrs=["0x401000"])                # unique byte signature
make_signature_for_function(addrs=["decrypt_payload"])
export_funcs(addrs=["main"], format="json")       # json | c_header | prototypes
int_convert(inputs=["0x401000", "4198400"])       # ALWAYS use this for base conversion
py_eval(code="import idautils; print(list(idautils.Functions())[:10])")
```

## Typical flows

**Malware capability mapping**
`survey_binary` → imports (network? crypto? registry?) → `find_regex("http|socket")` →
`xrefs_to` the string → `decompile` the referencing function → `trace_data_flow` on the crypto
parameters (backward, to find the key source) → rename/comment as you go.

**License/serial check**
`find_regex("serial|license|register|invalid")` → `xrefs_to` → `analyze_function` the validator →
`callgraph(depth 2)` for callers → `patch_asm` the conditional jump on a copy → re-decompile to
confirm.

**Vulnerability confirmation**
`entity_query(kind="imports", filter="strcpy|sprintf|gets")` → `xrefs_to` each sink →
`analyze_function` the calling function → `stack_frame` for buffer sizes → `trace_data_flow`
backward on the size/pointer argument to prove attacker control.
