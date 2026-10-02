#!/usr/bin/env bash
# Run the same checks CI runs — locally, before you push.
#   ./tools/check.sh
set -euo pipefail
cd "$(dirname "$0")/.."

ok(){ printf '  \033[32m✓\033[0m %s\n' "$1"; }

echo "SploitAgent — local checks"

python3 -m py_compile tools/catalog.py tools/console/server.py tools/hooks/*.py bench/*.py
ok "python files compile"

bash -n sploit install.sh bench/*.sh
ok "shell syntax"

if command -v shellcheck >/dev/null 2>&1; then
  shellcheck --severity=error sploit install.sh
  ok "shellcheck (errors)"
else
  echo "  · shellcheck not installed — skipping (CI still runs it)"
fi

python3 -c "import json; json.load(open('schemas/skill.schema.json'))"
ok "skill schema is valid JSON"

python3 tools/catalog.py validate

python3 tools/catalog.py check-counts

python3 tools/catalog.py catalog >/dev/null
python3 tools/catalog.py coverage >/dev/null
if ! git diff --quiet -- CATALOG.md COVERAGE.md docs/skills.json; then
  echo "  ✗ generated files are stale — commit these:"
  git --no-pager diff --stat -- CATALOG.md COVERAGE.md docs/skills.json
  exit 1
fi
ok "generated indexes up to date"

printf '\n\033[32mAll checks passed.\033[0m\n'
