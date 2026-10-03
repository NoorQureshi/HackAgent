# Protocol reverse cheat sheet — layouts, decoders, one-liners

Companion to `SKILL.md` (which teaches the four-phase method). Open this for the patterns and
exact commands.

## Common layout patterns

| Pattern | Tell | Watch for |
|---|---|---|
| Fixed header + body | first 2/4 bytes = length | does the length include the header? endianness? |
| Magic bytes | constant prefix, e.g. `0xDEAD` | great for re-syncing a TCP stream into frames |
| TLV | repeating type-length-value | the type enum *is* your message dictionary |
| Protobuf | low-byte field tags, varints | `protoc --decode_raw` reads it blind |
| Encrypted frame | high entropy, no plaintext markers | look for the nonce/IV adjacent to the ciphertext |

## Minimal Python frame parser skeleton

```python
import struct

def parse_frame(buf: bytes):
    magic, length, msg_type = struct.unpack_from(">IHI", buf, 0)  # big-endian: u32, u16, u32
    body = buf[10:10 + length]
    return {"magic": magic, "type": msg_type, "body": body}
```

Adjust the format string per target: `>` big-endian / `<` little-endian; `I` u32, `H` u16,
`B` u8, `Q` u64.

## tshark / Wireshark one-liners

```bash
# Dump TCP payloads of one port, hex, one per line
tshark -r cap.pcap -Y "tcp.port==4433" -T fields -e tcp.payload | head

# Frame number + direction + payload (triage view)
tshark -r cap.pcap -T fields -e frame.number -e ip.src -e tcp.payload

# Follow one stream as raw bytes
tshark -r cap.pcap -qz follow,tcp,raw,0

# Split a capture per stream for per-session analysis
tshark -r cap.pcap -q -z conv,tcp
```

## Protobuf without a .proto

```bash
# Quick structural read (field numbers + wire types)
protoc --decode_raw < msg.bin

# Rebuild a usable .proto from samples
pip install blackboxprotobuf
python - <<'EOF'
import blackboxprotobuf
msg, typedef = blackboxprotobuf.decode_message(open('msg.bin','rb').read())
print(typedef); print(msg)
EOF
```

gRPC: body = 1-byte compression flag + 4-byte big-endian length + protobuf message; the rest
of the protocol rides in HTTP/2 headers (`api-grpc` for the attack side).

## Checksums / integrity fields

- Byte count constant per message type, changes with any body byte → checksum/CRC. Try
  `crc32`, `crc16-ccitt`, or a simple sum over the body; brute-force the polynomial with
  `reveng` if needed.
- 16–32 byte field, changes fully on any 1-bit flip → hash or HMAC. Test plain `md5`/`sha256`
  of body, body+header, body+timestamp before assuming a keyed MAC; a keyed HMAC means the key
  is in the client (`reverse-eng-binary-triage` / `reverse-eng-js`).
