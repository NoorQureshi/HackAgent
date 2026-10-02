#!/usr/bin/env bash
# target_juiceshop.sh — lifecycle + scoring adapter for the OWASP Juice Shop bench target.
#
#   up      start Juice Shop on 127.0.0.1:3000 and wait until it answers
#   down    stop it
#   reset   restart (fresh in-memory state, fresh log)
#   status  print "up" or "down"
#   solved  print solved challenge names, one per line, parsed from the target log
#   count   print the total number of challenges (from /api/Challenges)
#
# Interface is generic on purpose: a second target adapter only needs these subcommands.
set -euo pipefail
cd "$(dirname "$0")"

BASE="$(pwd)/.targets/juice-shop"
APP="$BASE/app"
LOG="$BASE/target.log"
PIDF="$BASE/target.pid"
URL="http://127.0.0.1:3000"
NODE_RUNTIME="${BENCH_NODE_RUNTIME:-node@22}"

need_app(){ [ -d "$APP" ] || { echo "target not installed — run: python3 bench/run.py setup" >&2; exit 1; }; }

node_bin(){
  # The prebuilt zip's native modules need the matching node major; the `node` npm
  # package ships standalone binaries. Resolve once through npx, then exec it directly
  # so the pid we track is the server itself (npx would fork a child).
  local cachef="$BASE/node-bin.path"
  if [ ! -s "$cachef" ]; then
    npx -y "$NODE_RUNTIME" -p 'process.execPath' > "$cachef" 2>/dev/null
  fi
  cat "$cachef"
}

is_up(){ curl -sf --max-time 2 "$URL" >/dev/null 2>&1; }

do_up(){
  need_app
  if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then echo "already up"; return 0; fi
  if is_up; then echo "port 3000 is already served by another process — refusing to start" >&2; exit 1; fi
  : > "$LOG"   # fresh log per start — `solved` parses this file
  local bin; bin="$(node_bin)"
  (
    cd "$APP"
    NO_COLOR=1 nohup "$bin" build/app.js >>"$LOG" 2>&1 </dev/null &
    echo $! >"$PIDF"
  )
  local i
  for i in $(seq 1 90); do
    is_up && { echo "up → $URL (log: $LOG)"; return 0; }
    kill -0 "$(cat "$PIDF")" 2>/dev/null || { echo "target died on startup — last log lines:" >&2; tail -n 15 "$LOG" >&2; exit 1; }
    sleep 1
  done
  echo "target did not come up within 90s — see $LOG" >&2
  exit 1
}

do_down(){
  local pid=""
  [ -f "$PIDF" ] && pid="$(cat "$PIDF")"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 10); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
    kill -9 "$pid" 2>/dev/null || true
  fi
  # last resort: anything still listening on our port that looks like the target
  local stray
  for stray in $(lsof -nP -iTCP:3000 -sTCP:LISTEN -t 2>/dev/null || true); do
    if ps -p "$stray" -o command= | grep -q "app.js"; then kill -9 "$stray" 2>/dev/null || true; fi
  done
  # wait until the port actually stops answering, so `reset` can't race the old process
  for _ in $(seq 1 15); do is_up || break; sleep 1; done
  rm -f "$PIDF"
  echo "down"
}

do_solved(){
  [ -f "$LOG" ] || return 0
  # Log lines look like:  info: Solved 1-star errorHandlingChallenge (Error Handling)
  local esc; esc="$(printf '\033')"
  sed -E "s/${esc}\[[0-9;]*[A-Za-z]//g" "$LOG" \
    | grep 'Solved [0-9]*-star' \
    | sed -E 's/^.*\(([^()]*)\)[[:space:]]*$/\1/' \
    | sort -u || true   # grep exits 1 when nothing solved yet — that's data, not an error
}

do_count(){
  # /api/Challenges can answer empty while the app is still initializing — retry
  local n i
  for i in $(seq 1 30); do
    if n="$(curl -sf --max-time 5 "$URL/api/Challenges" 2>/dev/null | python3 -c "import json,sys; print(len(json.load(sys.stdin)['data']))" 2>/dev/null)"; then
      echo "$n"; return 0
    fi
    sleep 1
  done
  echo "could not read challenge count from $URL/api/Challenges" >&2
  return 1
}

cmd="${1:-}"
case "$cmd" in
  up)     do_up ;;
  down)   do_down ;;
  reset)  do_down >/dev/null; do_up ;;
  status) if is_up; then echo "up"; else echo "down"; fi ;;
  solved) do_solved ;;
  count)  do_count ;;
  *) echo "usage: $0 {up|down|reset|status|solved|count}" >&2; exit 2 ;;
esac
