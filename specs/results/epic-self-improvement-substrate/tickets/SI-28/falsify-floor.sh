#!/usr/bin/env bash
# SI-28 falsification harness — BOTH arms of the cli-floor warning.
#
# A check that cannot be shown to FIRE is the defect it exists to catch, and
# this epic has already shipped one (`find` on an absent directory reporting
# "0 symlinks, ok"). So this runs the real `skt check` code path twice against
# two homes that differ in exactly one fact: the version their skill-manager
# pin reports.
#
# It does NOT downgrade the operator's brew install, and must not. A Skill
# Manager home's CLI is a PIN — `<home>/bin/cli/skill-manager`, resolved by
# `skt.publish._cli` — and `skt check` deliberately asks that pin rather than
# whatever is on PATH, because "the version THIS HOME runs" is the question
# (`_installed_cli_identity`'s docstring says so). Two scratch homes with two
# pins is therefore the honest way to vary the CLI, not a trick: it exercises
# the same function, on the same input, that a real old install would.
#
# Usage:  bash specs/results/.../SI-28/falsify-floor.sh <scratch-dir>
set -uo pipefail

REPO="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../../.." && pwd -P)"
SCRATCH="${1:?usage: falsify-floor.sh <scratch-dir>}"
SKT_ENTRY="$REPO/skills/skt/src/skt/cli.py"
PY="${SKT_PYTHON:-python3.12}"

test -f "$SKT_ENTRY" || { echo "no skt entrypoint at $SKT_ENTRY" >&2; exit 1; }
test -f "$REPO/bootstrap-floor.toml" || { echo "no floor manifest at repo root" >&2; exit 1; }

FLOOR="$(sed -n 's/^minimum = "\(.*\)"/\1/p' "$REPO/bootstrap-floor.toml" | head -n1)"
echo "floor declared in $REPO/bootstrap-floor.toml: $FLOOR"
test -n "$FLOOR" || { echo "could not read the declared floor" >&2; exit 1; }

make_home() {           # make_home <name> <version-it-reports>
  local name="$1" version="$2" home="$SCRATCH/$1/.skill-manager"
  rm -rf "$SCRATCH/$name"
  mkdir -p "$home/installed" "$home/bin/cli"
  cat > "$home/bin/cli/skill-manager" <<EOF
#!/usr/bin/env bash
# A stand-in for a home's CLI pin. Answers --version like the real one
# (release line, then build:/cli:) and refuses everything else, which is
# what an older CLI lacking a verb does anyway.
if [ "\${1:-}" = "--version" ]; then
  echo "skill-manager $version"
  echo "build:  artifact deadbeef built 2026-09-17T00:00:00Z (skill-manager.jar)"
  echo "cli:    \$0"
  exit 0
fi
exit 64
EOF
  chmod 0755 "$home/bin/cli/skill-manager"
  printf '%s' "$home"
}

run_check() {           # run_check <home> -> prints report, echoes rc
  local home="$1" out rc
  out="$(SKILL_MANAGER_HOME="$home" SKT_ARTIFACTS=0 "$PY" "$SKT_ENTRY" check 2>&1)"
  rc=$?
  printf '%s\n' "$out"
  echo "EXIT=$rc"
}

echo
echo "================ ARM 1: FIRES against an older CLI (0.28.1) ============"
OLD="$(make_home old 0.28.1)"
echo "\$ SKILL_MANAGER_HOME=$OLD $PY skills/skt/src/skt/cli.py check"
run_check "$OLD"

echo
echo "================ ARM 2: SILENT against a current CLI ($FLOOR) =========="
NEW="$(make_home new "$FLOOR")"
echo "\$ SKILL_MANAGER_HOME=$NEW $PY skills/skt/src/skt/cli.py check"
run_check "$NEW"

echo
echo "================ ARM 3: the operator's REAL installed CLI ============="
echo "\$ skill-manager --version"
skill-manager --version 2>&1 | head -n1
echo "\$ SKILL_MANAGER_HOME=$REPO/.skill-manager $PY skills/skt/src/skt/cli.py check"
run_check "$REPO/.skill-manager"
