#!/usr/bin/env python3
"""Render the README demo terminal session as a self-contained SMIL-animated SVG.

Reads a demo script (docs/demo.cast.txt) and replays it on a fixed timeline:
typed commands/prompts (typewriter + cursor), output lines fading in, a hold
on the final frame, then the loop restarts. Pure SMIL — animates inside <img>
embeds (GitHub README), no scripts, no external fonts/images, no foreignObject.

Looping trick: an invisible "loop" animation fires `end` every T seconds; every
other animation lists `begin="t; loop.end+t"` and a dur that expires at T, so
each pass resets to hidden and replays.

Script format:
  $ <command>     shell command, typed char by char (green $, bright text)
  > <text>        chat prompt, typed char by char (green >, bright text)
  # pause <sec>   beat (a trailing pause is the hold before the loop restarts)
  # <anything>    comment, ignored
  (blank line)    blank row
  <other text>    output line, fades in; color picked from the leading marker
                  (● skill load, ✓ success, ✔ summary) and the name/detail
                  column split (first run of 2+ spaces)

Run: python3 tools/demo_svg.py [script] [out.svg]
     --snapshot   render the static final frame instead (for layout checks)
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

W, BAR_H, RADIUS = 820, 38, 10
X0, SIZE, LEADING, PAD_TOP, PAD_BOT = 22, 14, 22, 26, 20
CHAR_W = SIZE * 0.6          # assumed advance — used for cursor geometry only
CMD_CPS, CHAT_CPS = 16.0, 22.0
FADE = 0.30
MAX_ROWS = 16

BG, BAR, BORDER = "#0d1117", "#161b22", "#30363d"
DOTS = ("#ff5f57", "#febc2e", "#28c840")
C_PROMPT, C_CMD = "#7ee787", "#e6edf3"
C_SKILL, C_OK, C_OKNAME = "#56d4dd", "#3fb950", "#7ee787"
C_DIM, C_BRIGHT = "#8b949e", "#f0f6fc"
FONT = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
TITLE = "claude — ~/work/js — OWASP Juice Shop (127.0.0.1:3000)"
ARIA = "Terminal replay: Claude Code with SploitAgent skills solves 9 of 116 OWASP Juice Shop challenges in 10 minutes"


def ts(v):
    """Format seconds deterministically: 3 decimals max, no trailing zeros."""
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s or "0"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def txt(s):
    # &#160; so alignment spaces survive renderers that ignore xml:space.
    return esc(s).replace(" ", "&#160;")


def parse(path):
    events = []
    for n, raw in enumerate(open(path, encoding="utf-8"), 1):
        line = raw.rstrip("\n")
        if line.startswith("#"):
            m = re.match(r"#\s*pause\s+([0-9.]+)\s*$", line)
            if m:
                events.append(("pause", float(m.group(1))))
            elif re.match(r"#\s*\S", line) and not line.startswith("##"):
                pass  # comment
            continue
        if not line.strip():
            events.append(("blank", ""))
        elif line.startswith("$ "):
            events.append(("cmd", line[2:]))
        elif line.startswith("> "):
            events.append(("chat", line[2:]))
        else:
            events.append(("out", line))
    if not events:
        sys.exit(f"{path}: no demo lines found")
    return events


def timeline(events):
    """Assign each visible line a row and a start time; return (lines, total)."""
    lines, t = [], 0.0
    for kind, text in events:
        if kind == "pause":
            t += text
        elif kind == "blank":
            lines.append(None)
        else:
            lines.append((kind, text, t))
            if kind == "cmd":
                t += len(text) / CMD_CPS
            elif kind == "chat":
                t += len(text) / CHAT_CPS
    return lines, t


def out_spans(text):
    """Color an output line: marker, name column, detail column."""
    m = re.match(r"^(●|✓|✔) (.*)$", text)
    if not m:
        return [(text, C_DIM, False)]
    mark, rest = m.groups()
    if mark == "✔":
        return [("✔ ", C_OK, True), (rest, C_BRIGHT, True)]
    parts = re.split(r"(\s{2,})", rest, maxsplit=1)
    name, detail = parts[0], "".join(parts[1:])
    if mark == "●":
        return [("● ", C_SKILL, False), (name, C_SKILL, False), (detail, C_DIM, False)]
    return [("✓ ", C_OK, False), (name, C_OKNAME, False), (detail, C_DIM, False)]


def begin_at(b, total):
    """Two begins per animation: first pass, then once per loop restart."""
    return f"{ts(b)}s; loop.end+{ts(b)}s"


def emit_typed(y, text, t0, cps, total, snapshot, cursor):
    prompt = "$ " if cps == CMD_CPS else "> "
    spans = []
    if snapshot:
        spans.append(f'<tspan fill="{C_PROMPT}">{txt(prompt)}</tspan>')
        spans.append(f'<tspan fill="{C_CMD}">{txt(text)}</tspan>')
    else:
        show = f'<set attributeName="visibility" to="visible" begin="{begin_at(t0, total)}" dur="{ts(total - t0)}s"/>'
        spans.append(f'<tspan fill="{C_PROMPT}" visibility="hidden">{txt(prompt)}{show}</tspan>')
        for i, ch in enumerate(text):
            b = t0 + i / cps
            cursor.append((b, X0 + (len(prompt) + i + 1) * CHAR_W, y))
            show = f'<set attributeName="visibility" to="visible" begin="{begin_at(b, total)}" dur="{ts(total - b)}s"/>'
            spans.append(f'<tspan fill="{C_CMD}" visibility="hidden">{txt(ch)}{show}</tspan>')
    return f'<text x="{X0}" y="{y}">{"".join(spans)}</text>'


def emit_out(y, text, b, total, snapshot):
    spans, bold = [], any(s[2] for s in out_spans(text))
    for chunk, color, _ in out_spans(text):
        spans.append(f'<tspan fill="{color}">{txt(chunk)}</tspan>')
    if snapshot:
        anim, opacity = "", "1"
    else:
        frac = ts(FADE / (total - b))
        anim = (f'<animate attributeName="opacity" values="0;1;1" keyTimes="0;{frac};1" '
                f'dur="{ts(total - b)}s" begin="{begin_at(b, total)}"/>')
        opacity = "0"
    weight = ' font-weight="700"' if bold else ""
    return f'<text x="{X0}" y="{y}" opacity="{opacity}"{weight}>{"".join(spans)}{anim}</text>'


def baseline(row):
    return BAR_H + PAD_TOP + row * LEADING


def render(lines, total, snapshot=False):
    n = len(lines)
    max_cols = max((len(t[1]) + 2 for t in lines if t), default=0)
    if X0 + max_cols * CHAR_W > W - 16:
        sys.exit(f"line too wide: {max_cols} cols does not fit {W}px window")

    cursor = []          # (time, x, y) keyframes for the block cursor
    body, first_typed_y = [], None
    for row, item in enumerate(lines):
        if item is None:
            continue
        kind, text, t0 = item
        y = baseline(row)
        if kind in ("cmd", "chat"):
            if first_typed_y is None:
                first_typed_y = y
            body.append(emit_typed(y, text, t0, CMD_CPS if kind == "cmd" else CHAT_CPS,
                                   total, snapshot, cursor))
        else:
            body.append(emit_out(y, text, t0, total, snapshot))
            cursor.append((t0, X0, baseline(row + 1)))  # park on the next (empty) row

    # Height fits the last text row and, if the cursor parks below it, that row too.
    lowest = max([baseline(n - 1)] + [y for _, _, y in cursor])
    h = lowest + PAD_BOT

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}"',
        f'  font-family="{FONT}" font-size="{SIZE}" xml:space="preserve" role="img" aria-label="{ARIA}">',
        f'<title>{esc(ARIA)}</title>',
        f'<rect width="{W}" height="{h}" rx="{RADIUS}" fill="{BG}"/>',
        f'<path d="M0 {RADIUS} A{RADIUS} {RADIUS} 0 0 1 {RADIUS} 0 H{W - RADIUS} '
        f'A{RADIUS} {RADIUS} 0 0 1 {W} {RADIUS} V{BAR_H} H0 Z" fill="{BAR}"/>',
        f'<line x1="0" y1="{BAR_H}" x2="{W}" y2="{BAR_H}" stroke="{BORDER}"/>',
    ]
    for i, c in enumerate(DOTS):
        svg.append(f'<circle cx="{20 + 20 * i}" cy="{BAR_H // 2}" r="6" fill="{c}"/>')
    svg.append(f'<text x="{W // 2}" y="{BAR_H // 2 + 4}" text-anchor="middle" font-size="12" '
               f'fill="{C_DIM}">{esc(TITLE)}</text>')
    if not snapshot:
        svg.append(f'<rect width="0" height="0" opacity="0">'
                   f'<animate id="loop" attributeName="opacity" values="0;0" dur="{ts(total)}s" '
                   f'repeatCount="indefinite"/></rect>')
    svg.extend(body)

    # Block cursor: x/y jump via discrete sets, opacity blinks on its own fast cycle.
    if snapshot:
        cx, cy = (X0, baseline(n - 1)) if not cursor else cursor[-1][1:]
        svg.append(f'<rect x="{cx:.1f}" y="{cy - 13}" width="{CHAR_W:.1f}" height="17" rx="2" '
                   f'fill="{C_CMD}" opacity="0.85"/>')
    else:
        sets = []
        px = py = None
        for t, x, y in sorted(cursor):
            for attr, prev, val in (("x", px, x), ("y", py, y - 13)):
                if val != prev:
                    sets.append(f'<set attributeName="{attr}" to="{val:.1f}" '
                                f'begin="{begin_at(t, total)}" dur="{ts(total - t)}s"/>')
            px, py = x, y - 13
        svg.append(f'<rect x="{cursor[0][1]:.1f}" y="{cursor[0][2] - 13:.1f}" '
                   f'width="{CHAR_W:.1f}" height="17" rx="2" fill="{C_CMD}">{"".join(sets)}'
                   f'<animate attributeName="opacity" values="1;0;1" keyTimes="0;0.5;1" '
                   f'dur="1.06s" repeatCount="indefinite"/></rect>')

    svg.append(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{h - 1}" rx="{RADIUS}" '
               f'fill="none" stroke="{BORDER}"/>')
    svg.append('</svg>')
    return "\n".join(svg) + "\n", h


def main():
    args = [a for a in sys.argv[1:] if a != "--snapshot"]
    snapshot = len(args) != len(sys.argv) - 1
    script = args[0] if args else os.path.join(ROOT, "docs", "demo.cast.txt")
    out = args[1] if len(args) > 1 else os.path.join(ROOT, "docs", "screenshots", "demo.svg")
    lines, total = timeline(parse(script))
    rows = len(lines)
    if rows > MAX_ROWS:
        print(f"warning: {rows} rows > {MAX_ROWS} visible lines", file=sys.stderr)
    svg, h = render(lines, total, snapshot)
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    mode = "snapshot" if snapshot else f"loop {ts(total)}s"
    print(f"wrote {out} ({len(svg.encode('utf-8'))} bytes, {W}x{h}, {rows} rows, {mode})")


if __name__ == "__main__":
    main()
