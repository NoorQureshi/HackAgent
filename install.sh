#!/usr/bin/env bash
# SploitAgent installer — expose the skill library to Claude Code.
#
# Claude Code discovers skills exactly one directory deep
# (~/.claude/skills/<name>/SKILL.md), but this library is organised by domain
# (skills/<domain>/<slug>/SKILL.md). This script bridges that by linking each
# skill's folder into the flat layout Claude Code expects. Slugs are globally
# unique, so there are no collisions between our own skills.
#
# Usage:
#   ./install.sh              # install for your user  (~/.claude/skills)
#   ./install.sh --project    # install into ./.claude/skills (current project)
#   ./install.sh --dest DIR   # install into DIR instead of the default (~/.claude/skills)
#   ./install.sh --copy       # copy instead of symlink (for throwaway/portable clones)
#   ./install.sh --quiet      # only print the summary line
#   ./install.sh --uninstall  # remove only the skills this installer created
#
# Re-running is safe: it refreshes our links and never touches other skills.
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
    -h|--help)   sed -n '2,19p' "$0"; exit 0 ;;
    "")          : ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

if   [ -n "$DEST_OVERRIDE" ]; then DEST="$DEST_OVERRIDE"
elif [ "$SCOPE" = "project" ]; then DEST="$PWD/.claude/skills"
else DEST="$HOME/.claude/skills"; fi
MANIFEST="$DEST/.sploitagent-manifest"   # records the slugs we created, for clean uninstall

if [ "$ACTION" = "uninstall" ]; then
  n=0
  if [ -f "$MANIFEST" ]; then
    while IFS= read -r slug; do
      [ -n "$slug" ] || continue
      rm -rf "${DEST:?}/$slug" && n=$((n+1))
    done < "$MANIFEST"
    rm -f "$MANIFEST"
  fi
  echo "SploitAgent: removed $n skill(s) from $DEST"
  exit 0
fi

[ -d "$SRC" ] || { echo "error: skills/ not found next to install.sh" >&2; exit 1; }

mkdir -p "$DEST"
: > "$MANIFEST.tmp"
count=0; skipped=0
while IFS= read -r skill; do
  slug="$(basename "$(dirname "$skill")")"
  target="$DEST/$slug"
  # Only overwrite something we created before (listed in a prior manifest); never clobber a foreign skill.
  if [ -e "$target" ] && ! grep -qxF "$slug" "$MANIFEST" 2>/dev/null; then
    echo "  ! skipping '$slug' — an unrelated skill already exists at $target" >&2
    skipped=$((skipped+1)); continue
  fi
  rm -rf "$target"
  if [ "$MODE" = "copy" ]; then cp -R "$(dirname "$skill")" "$target"; else ln -s "$(dirname "$skill")" "$target"; fi
  echo "$slug" >> "$MANIFEST.tmp"
  count=$((count+1))
done < <(find "$SRC" -mindepth 3 -maxdepth 3 -name SKILL.md | sort)
mv "$MANIFEST.tmp" "$MANIFEST"

echo "SploitAgent: installed $count skill(s) into $DEST"
[ "$skipped" -gt 0 ] && echo "  ($skipped skipped — a different skill already occupies that name)"
[ "$QUIET" -eq 1 ] && exit 0
cat <<EOF

Done. Open Claude Code and it loads the matching skill for each task.
  - scope first: every engagement starts with tradecraft-scope-roe
  - uninstall:   ./install.sh$( [ "$SCOPE" = project ] && echo ' --project' ) --uninstall
Authorized security work only.
EOF
