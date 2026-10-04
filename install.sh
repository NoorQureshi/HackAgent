#!/usr/bin/env bash
# SploitAgent installer — expose the skill library to every AI agent on this machine.
#
# Claude Code discovers skills exactly one directory deep
# (~/.claude/skills/<name>/SKILL.md), but this library is organised by domain
# (skills/<domain>/<slug>/SKILL.md). This script bridges that by linking each
# skill's folder into the flat layout Claude Code expects. Slugs are globally
# unique, so there are no collisions between our own skills.
#
# The default (user-scope) install then wires every other detected agent:
#   - native global skills directory → the same links (Kimi Code ~/.kimi-code/skills,
#     Cursor ~/.cursor/skills);
#   - global instructions file → a small MANAGED BLOCK pointing at this repo and its
#     routing table (Codex ~/.codex/AGENTS.md, Gemini CLI ~/.gemini/GEMINI.md,
#     OpenCode ~/.config/opencode/AGENTS.md), wrapped in begin/end markers so
#     --uninstall removes exactly that block.
# An agent is configured when its config dir exists OR its CLI is on PATH.
#
# Usage:
#   ./install.sh              # install for your user  (~/.claude/skills + detected agents)
#   ./install.sh --project    # install into ./.claude/skills (current project; no global agent wiring)
#   ./install.sh --dest DIR   # install into DIR instead of the default (~/.claude/skills)
#   ./install.sh --copy       # copy instead of symlink (for throwaway/portable clones)
#   ./install.sh --quiet      # only print the summary line
#   ./install.sh --uninstall  # remove only the skills/blocks this installer created
#
# Re-running is safe: it refreshes our links, replaces (never duplicates) managed
# blocks, and never touches other skills or your own edits outside the markers.
set -euo pipefail

# Resolve this script's real location even when invoked via a symlink.
# BSD/macOS-safe: no `readlink -f`.
__src="${BASH_SOURCE[0]}"
while [ -h "$__src" ]; do
  __dir="$(cd -P "$(dirname "$__src")" && pwd)"
  __src="$(readlink "$__src")"
  case "$__src" in /*) ;; *) __src="$__dir/$__src" ;; esac
done
REPO_DIR="$(cd -P "$(dirname "$__src")" && pwd)"
SRC="$REPO_DIR/skills"

MODE="link"; SCOPE="user"; ACTION="install"; DEST_OVERRIDE=""; QUIET=0
while [ $# -gt 0 ]; do
  case "${1:-}" in
    --project)   SCOPE="project" ;;
    --copy)      MODE="copy" ;;
    --quiet)     QUIET=1 ;;
    --uninstall) ACTION="uninstall" ;;
    --dest)      DEST_OVERRIDE="${2:-}"; shift ;;
    --dest=*)    DEST_OVERRIDE="${1#--dest=}" ;;
    -h|--help)   sed -n '2,28p' "$0"; exit 0 ;;
    "")          : ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

if   [ -n "$DEST_OVERRIDE" ]; then DEST="$DEST_OVERRIDE"
elif [ "$SCOPE" = "project" ]; then DEST="$PWD/.claude/skills"
else DEST="$HOME/.claude/skills"; fi
MANIFEST="$DEST/.sploitagent-manifest"   # records the slugs we created, for clean uninstall
AGENTS_MANIFEST="$DEST/.sploitagent-agents"  # records the other agents we wired (name/kind/path)

# Global agent wiring only makes sense for the default user-scope install.
GLOBAL=0
if [ "$SCOPE" = "user" ] && [ -z "$DEST_OVERRIDE" ]; then GLOBAL=1; fi

BLOCK_BEGIN='<!-- BEGIN SPLOITAGENT MANAGED BLOCK'
BLOCK_END='<!-- END SPLOITAGENT MANAGED BLOCK -->'

tilde(){ printf '%s' "${1/#$HOME/~}"; }

# Link (or copy) every skill into a flat skills dir. Prints "<count> <skipped>".
link_skills(){
  local dest="$1"
  local manifest="$dest/.sploitagent-manifest"
  local skill slug target count=0 skipped=0
  mkdir -p "$dest"
  : > "$manifest.tmp"
  while IFS= read -r skill; do
    slug="$(basename "$(dirname "$skill")")"
    target="$dest/$slug"
    # Only overwrite something we created before (listed in a prior manifest); never clobber a foreign skill.
    if [ -e "$target" ] && ! grep -qxF "$slug" "$manifest" 2>/dev/null; then
      echo "  ! skipping '$slug' — an unrelated skill already exists at $target" >&2
      skipped=$((skipped+1)); continue
    fi
    rm -rf "$target"
    if [ "$MODE" = "copy" ]; then cp -R "$(dirname "$skill")" "$target"; else ln -s "$(dirname "$skill")" "$target"; fi
    echo "$slug" >> "$manifest.tmp"
    count=$((count+1))
  done < <(find "$SRC" -mindepth 3 -maxdepth 3 -name SKILL.md | sort)
  mv "$manifest.tmp" "$manifest"
  echo "$count $skipped"
}

# Remove the skills a previous install linked into a dir. Prints the count removed.
unlink_skills(){
  local dest="$1"
  local manifest="$dest/.sploitagent-manifest" slug n=0
  if [ -f "$manifest" ]; then
    while IFS= read -r slug; do
      [ -n "$slug" ] || continue
      rm -rf "${dest:?}/$slug" && n=$((n+1))
    done < "$manifest"
    rm -f "$manifest"
  fi
  echo "$n"
}

write_block(){
  cat <<EOF
$BLOCK_BEGIN — added by install.sh; do not edit between these markers -->
## SploitAgent — security skill library (authorized testing only)

A library of security skills for AI agents lives at: $REPO_DIR
- Confirm scope FIRST: read \`skills/tradecraft/tradecraft-scope-roe/SKILL.md\` there and
  refuse anything outside the user's authorized targets.
- For any security task, pick the matching skill via \`data/routing.json\` or \`CATALOG.md\`
  in that repo, then read \`skills/<domain>/<slug>/SKILL.md\` and follow its method.
- Full operating guide: \`AGENTS.md\` in that repo.
$BLOCK_END
EOF
}

# Strip our managed block (begin→end markers inclusive) from a file, if present.
remove_block(){
  local file="$1" tmp
  [ -f "$file" ] || return 0
  grep -qF "$BLOCK_BEGIN" "$file" || return 0
  tmp="$file.sploitagent-tmp.$$"
  awk -v b="$BLOCK_BEGIN" -v e="$BLOCK_END" '
    index($0, b) { inblk=1; next }
    inblk && index($0, e) { inblk=0; next }
    !inblk
  ' "$file" > "$tmp"
  mv "$tmp" "$file"
}

# Append (or refresh) our managed block in a global instructions file.
add_block(){
  local file="$1"
  mkdir -p "$(dirname "$file")"
  remove_block "$file"   # idempotent: replace an existing block instead of duplicating it
  if [ -s "$file" ]; then printf '\n' >> "$file"; fi
  write_block >> "$file"
}

if [ "$ACTION" = "uninstall" ]; then
  n="$(unlink_skills "$DEST")"
  echo "SploitAgent: removed $n skill(s) from $DEST"
  if [ "$GLOBAL" -eq 1 ] && [ -f "$AGENTS_MANIFEST" ]; then
    while IFS='	' read -r name kind path; do
      [ -n "$name" ] || continue
      case "$kind" in
        skills)
          m="$(unlink_skills "$path")"
          echo "  ✔ $name — removed $m skill(s) from $(tilde "$path")"
          ;;
        block)
          if [ -f "$path" ] && grep -qF "$BLOCK_BEGIN" "$path"; then
            remove_block "$path"
            echo "  ✔ $name — removed managed block from $(tilde "$path")"
          else
            echo "  – $name — nothing to remove in $(tilde "$path")"
          fi
          ;;
      esac
    done < "$AGENTS_MANIFEST"
    rm -f "$AGENTS_MANIFEST"
  fi
  exit 0
fi

[ -d "$SRC" ] || { echo "error: skills/ not found next to install.sh" >&2; exit 1; }

res="$(link_skills "$DEST")"
count="${res%% *}"; skipped="${res##* }"

echo "SploitAgent: installed $count skill(s) into $DEST"
[ "$skipped" -gt 0 ] && echo "  ($skipped skipped — a different skill already occupies that name)"

# --- wire the other detected agents (user scope only) -------------------------
if [ "$GLOBAL" -eq 1 ]; then
  : > "$AGENTS_MANIFEST.tmp"
  KIMI_HOME="${KIMI_CODE_HOME:-$HOME/.kimi-code}"
  [ "$QUIET" -eq 0 ] && echo "" && echo "Agent wiring:"
  [ "$QUIET" -eq 0 ] && printf '  ✔ %-10s %s skill(s) linked → %s\n' claude "$count" "$(tilde "$DEST")"
  # name|config dir|CLIs (space-separated)|kind|target
  while IFS='|' read -r name cfg cmds kind target; do
    [ -n "$name" ] || continue
    found=0
    if [ -n "$cfg" ] && [ -d "$cfg" ]; then found=1; fi
    if [ "$found" -eq 0 ]; then
      for c in $cmds; do
        if command -v "$c" >/dev/null 2>&1; then found=1; break; fi
      done
    fi
    if [ "$found" -eq 0 ]; then
      [ "$QUIET" -eq 0 ] && printf '  – %-10s skipped (no %s, no CLI on PATH)\n' "$name" "$(tilde "$cfg")"
      continue
    fi
    case "$kind" in
      skills)
        res="$(link_skills "$target")"
        wcount="${res%% *}"; wskipped="${res##* }"
        printf '%s\t%s\t%s\n' "$name" skills "$target" >> "$AGENTS_MANIFEST.tmp"
        [ "$QUIET" -eq 0 ] && printf '  ✔ %-10s %s skill(s) linked → %s\n' "$name" "$wcount" "$(tilde "$target")"
        [ "$wskipped" -gt 0 ] && echo "    ($wskipped skipped — a different skill already occupies that name)"
        ;;
      block)
        add_block "$target"
        printf '%s\t%s\t%s\n' "$name" block "$target" >> "$AGENTS_MANIFEST.tmp"
        [ "$QUIET" -eq 0 ] && printf '  ✔ %-10s managed block → %s\n' "$name" "$(tilde "$target")"
        ;;
    esac
  done <<AGENTS
kimi-code|$KIMI_HOME|kimi kimi-code|skills|$KIMI_HOME/skills
cursor|$HOME/.cursor|cursor cursor-agent|skills|$HOME/.cursor/skills
codex|$HOME/.codex|codex|block|$HOME/.codex/AGENTS.md
gemini|$HOME/.gemini|gemini|block|$HOME/.gemini/GEMINI.md
opencode|$HOME/.config/opencode|opencode|block|$HOME/.config/opencode/AGENTS.md
AGENTS
  mv "$AGENTS_MANIFEST.tmp" "$AGENTS_MANIFEST"
fi

[ "$QUIET" -eq 1 ] && exit 0
cat <<EOF

Done. Open your agent — Claude Code, Kimi Code, Cursor, Codex, Gemini, OpenCode — and it loads the matching skill for each task.
  - scope first: every engagement starts with tradecraft-scope-roe
  - uninstall:   ./install.sh$( [ "$SCOPE" = project ] && echo ' --project' ) --uninstall
Authorized security work only.
EOF
